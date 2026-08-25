#!/usr/bin/env bash
# deploy.sh — production environment full deployment script
# Usage: sudo ./deploy.sh [--only=<component>]
#
# Components: nginx | wireguard | systemd | all (default)
#
# Requirements: run as root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(dirname "$SCRIPT_DIR")"

log() { echo "[deploy] $*"; }
die() { echo "[deploy] ERROR: $*" >&2; exit 1; }

# --- Argument parsing ---
COMPONENT="${1:-all}"
ONLY_COMPONENT=""
if [[ "$COMPONENT" == --only=* ]]; then
    ONLY_COMPONENT="${COMPONENT#--only=}"
    COMPONENT="single"
fi

need_root() {
    [[ $EUID -eq 0 ]] || die "must be run as root (use sudo)"
}

# --- Install functions ---

install_nginx() {
    need_root
    log "Installing Nginx reverse proxy config..."
    local dest="/etc/nginx/sites-available/reverse-proxy.conf"
    cp "$WORKSPACE_DIR/nginx-reverse-proxy.conf" "$dest"
    chmod 644 "$dest"
    ln -sf "$dest" /etc/nginx/sites-enabled/reverse-proxy.conf
    # Disable default site if it exists
    [[ -L /etc/nginx/sites-enabled/default ]] && rm -f /etc/nginx/sites-enabled/default
    "$SCRIPT_DIR/nginx-reload.sh"
    log "Nginx installed."
}

install_wireguard() {
    need_root
    log "Installing WireGuard VPN config..."
    local dest="/etc/wireguard/wg0.conf"
    cp "$WORKSPACE_DIR/wireguard/wg0.conf" "$dest"
    chmod 600 "$dest"
    systemctl enable wg-quick@wg0
    log "WireGuard installed. Start with: systemctl start wg-quick@wg0"
    log "REMINDER: edit $dest to add real PrivateKey and peer PublicKeys before starting."
}

install_systemd() {
    need_root
    log "Installing systemd unit files..."
    local unit_dir="/etc/systemd/system"
    cp "$WORKSPACE_DIR/systemd/deployment-manager.service" "$unit_dir/"
    cp "$WORKSPACE_DIR/systemd/certbot-renewal.service" "$unit_dir/"
    cp "$WORKSPACE_DIR/systemd/certbot-renewal.timer" "$unit_dir/"
    chmod 644 "$unit_dir"/*.service "$unit_dir"/*.timer
    systemctl daemon-reload
    systemctl enable certbot-renewal.timer
    systemctl start certbot-renewal.timer
    log "systemd units installed and timer started."
}

install_scripts() {
    need_root
    log "Installing helper scripts..."
    local script_dest="/opt/deploy"
    mkdir -p "$script_dest"
    cp "$WORKSPACE_DIR/scripts/"*.sh "$script_dest/"
    chmod +x "$script_dest"/*.sh
    log "Scripts installed to $script_dest/"
}

# --- Main ---
case "$COMPONENT" in
    all)
        install_scripts
        install_nginx
        install_wireguard
        install_systemd
        log "=== Full deployment complete ==="
        log "Next steps:"
        log "  1. Edit /etc/wireguard/wg0.conf — add real keys"
        log "  2. systemctl start wg-quick@wg0"
        log "  3. Obtain SSL cert: certbot --nginx -d your-domain.com"
        ;;
    single)
        case "$ONLY_COMPONENT" in
            nginx)      install_nginx ;;
            wireguard)  install_wireguard ;;
            systemd)    install_systemd ;;
            scripts)    install_scripts ;;
            *)          die "unknown component: $ONLY_COMPONENT (nginx|wireguard|systemd|scripts)" ;;
        esac
        ;;
    *) die "Usage: $0 [--only=<component>]" ;;
esac
