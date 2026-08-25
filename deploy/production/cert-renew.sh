#!/usr/bin/env bash
# cert-renew.sh — Let's Encrypt SSL certificate renewal helper
# Usage: sudo ./cert-renew.sh [--dry-run]
# Installs certs to /etc/letsencrypt/

set -euo pipefail

LETSENCRYPT_WEBROOT="${LETSENCRYPT_WEBROOT:-/var/www/letsencrypt}"
DRY_RUN=false

# Parse arguments
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "[cert-renew] DRY RUN MODE — no changes will be made"
fi

# Verify webroot exists (required for ACME challenge)
if [[ ! -d "$LETSENCRYPT_WEBROOT" ]]; then
    echo "[cert-renew] ERROR: ACME webroot not found at $LETSENCRYPT_WEBROOT"
    echo "[cert-renew] Create it with: sudo mkdir -p $LETSENCRYPT_WEBROOT"
    exit 1
fi

# Ensure nginx is running so ACME challenges can be served
if ! systemctl is-active --quiet nginx; then
    echo "[cert-renew] WARNING: nginx is not running. Starting it..."
    systemctl start nginx
fi

CERTBOT_CMD=(certbot renew)

if $DRY_RUN; then
    echo "[cert-renew] Running certbot renew --dry-run ..."
    certbot renew --dry-run
    echo "[cert-renew] Dry run complete. Cert would be renewed if near expiry."
else
    echo "[cert-renew] Running certbot renew ..."
    certbot renew --quiet --deploy-hook "systemctl reload nginx"
    echo "[cert-renew] Renewal check complete. See journalctl -u certbot-renewal for details."
fi
