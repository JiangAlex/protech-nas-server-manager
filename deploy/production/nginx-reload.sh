#!/usr/bin/env bash
# nginx-reload.sh — safely test and reload Nginx configuration
# Usage: sudo ./nginx-reload.sh
#
# Tests config BEFORE reloading to avoid downtime if there's a syntax error.

set -euo pipefail

NGINX_CONF_TEST=("/usr/sbin/nginx" "-t")
NGINX_RELOAD=("systemctl" "reload" "nginx")

echo "[nginx-reload] Testing nginx configuration..."
if "${NGINX_CONF_TEST[@]}"; then
    echo "[nginx-reload] Configuration syntax OK — reloading nginx..."
    "${NGINX_RELOAD[@]}"
    echo "[nginx-reload] nginx reloaded successfully."
else
    echo "[nginx-reload] ERROR: nginx configuration test failed. NOT reloading."
    echo "[nginx-reload] Run 'sudo nginx -t' for detailed error output."
    exit 1
fi
