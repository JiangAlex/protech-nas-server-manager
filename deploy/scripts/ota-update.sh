#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# ProTech NAS — OTA System Update Script
# Standalone script that can be triggered by cron or manually.
#
# Usage:
#   ./scripts/ota-update.sh
#   ./scripts/ota-update.sh --check-only   # Only check, don't apply
#
# Prerequisites: curl, jq, tar, git, python3-venv
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ─── Configuration (override via environment or .env) ─────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load .env if exists
if [ -f "$PROJECT_ROOT/backend/.env" ]; then
  set -a
  source "$PROJECT_ROOT/backend/.env"
  set +a
fi

SERVER_URL="${OTA_SERVER_URL:-http://localhost:8060}"
DEVICE_ID="${OTA_DEVICE_ID:-1}"
DEPLOY_MODE="${OTA_DEPLOY_MODE:-systemd}"
APP_DIR="${OTA_APP_DIR:-/opt/protech-nas}"
WEB_DIR="${OTA_WEB_DIR:-/var/www/protech-nas}"

# Use project root as APP_DIR in dev mode
if [ ! -d "$APP_DIR" ] && [ -d "$PROJECT_ROOT/.git" ]; then
  APP_DIR="$PROJECT_ROOT"
fi

LOCK_FILE="/tmp/protech-nas-update.lock"
LOG_FILE="/var/log/protech-nas-update.log"
CHECK_ONLY=false

# ─── Parse arguments ──────────────────────────────────────────────────────────

for arg in "$@"; do
  case $arg in
    --check-only)
      CHECK_ONLY=true
      ;;
    --help|-h)
      echo "Usage: $0 [--check-only] [--help]"
      echo "  --check-only  Only check for updates, don't apply"
      exit 0
      ;;
  esac
done

# ─── Utilities ────────────────────────────────────────────────────────────────

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

cleanup() {
  rm -f "$LOCK_FILE" 2>/dev/null || true
}
trap cleanup EXIT

# ─── Lock check ──────────────────────────────────────────────────────────────

if [ -f "$LOCK_FILE" ]; then
  LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    log "ERROR: Update already in progress (PID: $LOCK_PID)"
    exit 1
  fi
  # Stale lock file
  rm -f "$LOCK_FILE"
fi

echo $$ > "$LOCK_FILE"

# ─── Read current version ────────────────────────────────────────────────────

CURRENT_VERSION=$(cat "$APP_DIR/VERSION" 2>/dev/null || echo "unknown")
CURRENT_HASH=$(cd "$APP_DIR" && git rev-parse --short HEAD 2>/dev/null || echo "unknown")

log "Current version: $CURRENT_VERSION (hash: $CURRENT_HASH)"
log "OTA Server: $SERVER_URL | Device ID: $DEVICE_ID | Mode: $DEPLOY_MODE"

# ─── Step 1: Check for updates ───────────────────────────────────────────────

log "Checking for updates..."

RESPONSE=$(curl -s --max-time 15 -X POST "$SERVER_URL/api/ota/nas/check" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"current_version\": \"$CURRENT_VERSION\",
    \"current_git_hash\": \"$CURRENT_HASH\",
    \"device_type\": \"nas\",
    \"deploy_mode\": \"$DEPLOY_MODE\"
  }" 2>/dev/null) || {
  log "ERROR: Cannot connect to OTA server at $SERVER_URL"
  exit 1
}

UPDATE_AVAILABLE=$(echo "$RESPONSE" | jq -r '.update_available' 2>/dev/null || echo "false")

if [ "$UPDATE_AVAILABLE" != "true" ]; then
  log "System is up to date."
  exit 0
fi

LATEST_VERSION=$(echo "$RESPONSE" | jq -r '.latest_version')
CHANGELOG=$(echo "$RESPONSE" | jq -r '.changelog // ""')

log "New version available: $LATEST_VERSION"
[ -n "$CHANGELOG" ] && log "Changelog: $CHANGELOG"

if [ "$CHECK_ONLY" = true ]; then
  echo "update_available=true"
  echo "latest_version=$LATEST_VERSION"
  echo "changelog=$CHANGELOG"
  exit 0
fi

# ─── Step 2: Get download info ───────────────────────────────────────────────

log "Fetching download info..."

DOWNLOAD_INFO=$(curl -s --max-time 15 "$SERVER_URL/api/ota/nas/download/$DEVICE_ID" 2>/dev/null) || {
  log "ERROR: Cannot fetch download info"
  exit 1
}

TARGET_HASH=$(echo "$DOWNLOAD_INFO" | jq -r '.git_hash')
FRONTEND_URL=$(echo "$DOWNLOAD_INFO" | jq -r '.frontend_artifact_url // ""')
FRONTEND_CHECKSUM=$(echo "$DOWNLOAD_INFO" | jq -r '.frontend_checksum // ""')

if [ -z "$TARGET_HASH" ] || [ "$TARGET_HASH" = "null" ]; then
  log "ERROR: No target git hash in download info"
  exit 1
fi

log "Target: v$LATEST_VERSION (hash: $TARGET_HASH)"

# ─── Step 3: Backup ──────────────────────────────────────────────────────────

OLD_HASH=$(cd "$APP_DIR" && git rev-parse HEAD 2>/dev/null || echo "")
STATUS=""
ERROR=""

log "Backup: current hash=$OLD_HASH"

# ─── Step 4: Apply update ────────────────────────────────────────────────────

rollback() {
  log "Rolling back to $OLD_HASH..."
  cd "$APP_DIR"
  git checkout "$OLD_HASH" 2>/dev/null || true

  if [ "$DEPLOY_MODE" = "docker" ]; then
    docker compose up -d --build 2>/dev/null || true
  else
    cd backend
    source .venv/bin/activate 2>/dev/null || true
    pip install -r requirements.txt -q 2>/dev/null || true
    cd ..
    sudo systemctl restart protech-nas 2>/dev/null || true
    if [ -d "${WEB_DIR}.bak" ]; then
      sudo rm -rf "$WEB_DIR"
      sudo mv "${WEB_DIR}.bak" "$WEB_DIR"
    fi
  fi
}

# --- Git fetch + checkout ---
log "Pulling code..."
cd "$APP_DIR"

if ! git fetch origin main 2>&1; then
  ERROR="git fetch failed"
  STATUS="failed"
fi

if [ -z "$STATUS" ]; then
  if ! git checkout "$TARGET_HASH" 2>&1; then
    ERROR="git checkout $TARGET_HASH failed"
    STATUS="failed"
  fi
fi

# --- Deploy based on mode ---
if [ -z "$STATUS" ]; then
  if [ "$DEPLOY_MODE" = "docker" ]; then
    # Docker mode: rebuild containers
    log "Rebuilding Docker containers..."
    if ! docker compose up -d --build 2>&1; then
      ERROR="docker compose up failed"
      STATUS="failed"
    fi
  else
    # Systemd mode: pip install + frontend download + restart
    log "Installing backend dependencies..."
    cd "$APP_DIR/backend"
    source .venv/bin/activate

    if ! pip install -r requirements.txt -q 2>&1; then
      ERROR="pip install failed"
      STATUS="failed"
    fi
    cd "$APP_DIR"

    # Download frontend artifact
    if [ -z "$STATUS" ] && [ -n "$FRONTEND_URL" ] && [ "$FRONTEND_URL" != "null" ] && [ "$FRONTEND_URL" != "" ]; then
      log "Downloading frontend artifact..."
      TMPFILE=$(mktemp /tmp/frontend-XXXXXX.tar.gz)

      if ! curl -sf --max-time 120 "$SERVER_URL$FRONTEND_URL" -o "$TMPFILE" 2>/dev/null; then
        ERROR="frontend download failed"
        STATUS="failed"
        rm -f "$TMPFILE"
      fi

      # Verify checksum
      if [ -z "$STATUS" ] && [ -n "$FRONTEND_CHECKSUM" ] && [ "$FRONTEND_CHECKSUM" != "null" ]; then
        EXPECTED=$(echo "$FRONTEND_CHECKSUM" | sed 's/sha256://')
        ACTUAL=$(sha256sum "$TMPFILE" | awk '{print $1}')
        if [ "$EXPECTED" != "$ACTUAL" ]; then
          ERROR="frontend checksum mismatch (expected: $EXPECTED, got: $ACTUAL)"
          STATUS="failed"
          rm -f "$TMPFILE"
        fi
      fi

      # Deploy frontend
      if [ -z "$STATUS" ]; then
        # Backup existing
        if [ -d "$WEB_DIR" ]; then
          sudo cp -r "$WEB_DIR" "${WEB_DIR}.bak"
        fi
        sudo rm -rf "$WEB_DIR"
        sudo mkdir -p "$WEB_DIR"
        if ! sudo tar -xzf "$TMPFILE" -C "$WEB_DIR" --strip-components=1 2>&1; then
          ERROR="frontend extraction failed"
          STATUS="failed"
          # Restore backup
          sudo rm -rf "$WEB_DIR"
          sudo mv "${WEB_DIR}.bak" "$WEB_DIR" 2>/dev/null || true
        fi
        rm -f "$TMPFILE"
      fi
    fi

    # Restart service
    if [ -z "$STATUS" ]; then
      log "Restarting service..."
      if ! sudo systemctl restart protech-nas 2>&1; then
        ERROR="systemctl restart failed"
        STATUS="failed"
      fi
    fi
  fi
fi

# ─── Step 5: Health check ────────────────────────────────────────────────────

if [ -z "$STATUS" ]; then
  log "Waiting for service to start..."
  sleep 5

  HEALTH_OK=false
  for i in 1 2 3; do
    if curl -sf --max-time 5 http://localhost:8000/api/health > /dev/null 2>&1; then
      HEALTH_OK=true
      break
    fi
    sleep 2
  done

  if [ "$HEALTH_OK" = true ]; then
    STATUS="completed"
    # Update VERSION file
    echo "$LATEST_VERSION" > "$APP_DIR/VERSION"
    log "Health check passed. Update successful!"
  else
    ERROR="Health check failed after update"
    STATUS="failed"
  fi
fi

# ─── Step 6: Rollback if failed ──────────────────────────────────────────────

if [ "$STATUS" = "failed" ]; then
  log "ERROR: $ERROR"
  rollback
  STATUS="rolled_back"
  log "Rolled back to previous version."
fi

# Cleanup frontend backup
sudo rm -rf "${WEB_DIR}.bak" 2>/dev/null || true

# ─── Step 7: Report result ───────────────────────────────────────────────────

log "Reporting result: $STATUS"

curl -s --max-time 15 -X POST "$SERVER_URL/api/ota/nas/report" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"from_version\": \"$CURRENT_VERSION\",
    \"to_version\": \"$LATEST_VERSION\",
    \"to_git_hash\": \"$TARGET_HASH\",
    \"status\": \"$STATUS\",
    \"error_message\": \"$ERROR\"
  }" > /dev/null 2>&1 || true

log "Update finished: $STATUS (v$CURRENT_VERSION → v$LATEST_VERSION)"

if [ "$STATUS" = "completed" ]; then
  exit 0
else
  exit 1
fi
