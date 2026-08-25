#!/bin/bash
# ProTech NAS — Production Deployment Script
# 將 backend 設為 systemd service 開機自動啟動，frontend 透過 Nginx 提供服務
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SERVICE_USER="${NAS_USER:-$(whoami)}"
WEB_ROOT="/var/www/protech-nas"

echo "╔══════════════════════════════════════════════╗"
echo "║     ProTech NAS — Production Deployment      ║"
echo "╠══════════════════════════════════════════════╣"
echo "║  Project:  $PROJECT_DIR"
echo "║  User:     $SERVICE_USER"
echo "║  Web Root: $WEB_ROOT"
echo "╚══════════════════════════════════════════════╝"
echo ""

# ─── Pre-flight checks ───────────────────────────────────────────────────────
echo "[0/6] Pre-flight checks..."

if [ ! -f "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
    echo "  ⚠ Backend venv not found. Run scripts/setup_deps.sh first."
    exit 1
fi

if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "  ⚠ Backend .env not found. Creating from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "  ⚠ Please edit $BACKEND_DIR/.env and set SECRET_KEY!"
fi

if ! command -v nginx &> /dev/null; then
    echo "  ⚠ Nginx not installed. Run: sudo apt install nginx"
    exit 1
fi

echo "  ✓ All checks passed."
echo ""

# ─── RAID 1 HA detection ─────────────────────────────────────────────────────
DISK_COUNT=$(lsblk -d -n -o NAME,TYPE | awk '$2=="disk"' | wc -l)
if [ "$DISK_COUNT" -ge 2 ]; then
    if [ ! -e /dev/md0 ] && ! grep -q "md0" /proc/mdstat 2>/dev/null; then
        echo "╔══════════════════════════════════════════════════╗"
        echo "║  ℹ 偵測到 ${DISK_COUNT} 顆磁碟，建議設定 RAID 1 (HA)    ║"
        echo "║  執行：sudo bash scripts/setup-raid1-ha.sh       ║"
        echo "╚══════════════════════════════════════════════════╝"
        echo ""
    else
        echo "  ✓ RAID 1 (HA) already active."
        echo ""
    fi
fi

# ─── Step 1: Build frontend ──────────────────────────────────────────────────
echo "[1/6] Building frontend..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
echo "  ✓ Frontend built."
echo ""

# ─── Step 2: Deploy frontend to web root ─────────────────────────────────────
echo "[2/6] Deploying frontend to $WEB_ROOT..."
sudo mkdir -p "$WEB_ROOT"
sudo rm -rf "$WEB_ROOT"/*
sudo cp -r "$FRONTEND_DIR/dist/"* "$WEB_ROOT/"
sudo chown -R www-data:www-data "$WEB_ROOT"
echo "  ✓ Frontend deployed."
echo ""

# ─── Step 3: Install systemd service ─────────────────────────────────────────
echo "[3/6] Installing systemd service..."

# Generate service file with correct user/paths
sed -e "s|User=alex_chiang|User=$SERVICE_USER|g" \
    -e "s|Group=alex_chiang|Group=$SERVICE_USER|g" \
    -e "s|/home/alex_chiang/projects/protech-nas|$PROJECT_DIR|g" \
    "$SCRIPT_DIR/protech-nas.service" | sudo tee /etc/systemd/system/protech-nas.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable protech-nas
sudo systemctl restart protech-nas
echo "  ✓ Backend service enabled and started."
echo ""

# ─── Step 4: Configure Nginx ─────────────────────────────────────────────────
echo "[4/6] Configuring Nginx..."
sudo cp "$SCRIPT_DIR/protech-nas-nginx.conf" /etc/nginx/sites-available/protech-nas
sudo ln -sf /etc/nginx/sites-available/protech-nas /etc/nginx/sites-enabled/protech-nas

# Remove default site if it conflicts
if [ -L /etc/nginx/sites-enabled/default ]; then
    sudo rm -f /etc/nginx/sites-enabled/default
    echo "  (Removed default Nginx site)"
fi

# Test nginx config
if sudo nginx -t 2>&1 | grep -q "successful"; then
    sudo systemctl reload nginx
    echo "  ✓ Nginx configured and reloaded."
else
    echo "  ✗ Nginx config test failed:"
    sudo nginx -t
    exit 1
fi
echo ""

# ─── Step 5: Setup sudoers ───────────────────────────────────────────────────
echo "[5/6] Setting up sudoers for privileged operations..."
if [ ! -f /etc/sudoers.d/protech-nas ]; then
    sed "s/nas/$SERVICE_USER/g" "$SCRIPT_DIR/sudoers-protech-nas" | sudo tee /etc/sudoers.d/protech-nas > /dev/null
    sudo chmod 0440 /etc/sudoers.d/protech-nas
    if sudo visudo -c -f /etc/sudoers.d/protech-nas > /dev/null 2>&1; then
        echo "  ✓ Sudoers configured."
    else
        echo "  ✗ Sudoers syntax error! Removing..."
        sudo rm -f /etc/sudoers.d/protech-nas
        exit 1
    fi
else
    echo "  ✓ Sudoers already configured (skipped)."
fi
echo ""

# ─── Step 6: Enable Nginx on boot ────────────────────────────────────────────
echo "[6/6] Enabling Nginx on boot..."
sudo systemctl enable nginx
echo "  ✓ Nginx enabled."
echo ""

# ─── Done ────────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════╗"
echo "║          ✓ Deployment Complete!              ║"
echo "╠══════════════════════════════════════════════╣"
echo "║                                              ║"
echo "║  NAS Web UI:  http://$(hostname -I | awk '{print $1}')       "
echo "║  API Docs:    http://$(hostname -I | awk '{print $1}')/api/docs"
echo "║  Login:       admin / admin123               ║"
echo "║                                              ║"
echo "║  Commands:                                   ║"
echo "║    systemctl status protech-nas              ║"
echo "║    journalctl -u protech-nas -f              ║"
echo "║    systemctl restart protech-nas             ║"
echo "║                                              ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "⚠ Remember to change SECRET_KEY and default password in production!"
