# Production Environment Deployment Package

## Overview

Complete deployment configuration for a production environment with:
- Nginx reverse proxy (HTTP→HTTPS, rate limiting, WebSocket support)
- Let's Encrypt SSL with automatic renewal via certbot
- WireGuard VPN server
- systemd service units and timers

---

## File Structure

```
.
├── README.md
├── deploy.sh                        # Main deployment orchestrator (run as root)
├── nginx-reverse-proxy.conf          # Nginx site config
├── scripts/
│   ├── cert-renew.sh                 # Manual cert renewal helper
│   ├── deploy.sh                     # Component-specific installer
│   └── nginx-reload.sh               # Safe nginx config test + reload
├── systemd/
│   ├── certbot-renewal.service       # certbot renewal oneshot service
│   ├── certbot-renewal.timer         # Twice-daily renewal trigger
│   └── deployment-manager.service    # Application deployment service
└── wireguard/
    ├── client-wg0.conf               # Template: give each client one of these
    └── wg0.conf                      # Server-side WireGuard config
```

---

## Quick Start

```bash
# 1. Copy this entire directory to your server
# 2. Run the deploy script (run as root)
sudo ./deploy.sh

# 3. WireGuard: generate server keys and fill in real values
sudo wg genkey | tee /etc/wireguard/server_private.key
sudo cat /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
# Then edit /etc/wireguard/wg0.conf — replace <SERVER_PRIVATE_KEY>
# and add [Peer] blocks with real client public keys

# 4. Obtain SSL certificate (one-time)
sudo certbot --nginx -d your-domain.com -d your-other-domain.com

# 5. Start WireGuard
sudo systemctl start wg-quick@wg0
sudo systemctl enable wg-quick@wg0
```

---

## Component Details

### Nginx Reverse Proxy

Deploy: `/etc/nginx/sites-available/reverse-proxy.conf`

Features:
- HTTP→HTTPS redirect
- ACME challenge location for Let's Encrypt
- SSL/TLS with modern protocols and hardening headers
- Rate limiting: 30r/s general API, 5r/m for /auth/
- WebSocket proxy at /ws/ (with 24h read timeout)
- Gzip compression
- Separate upstreams for API (port 8000), static (port 8080), WebSocket (port 9000)
- Health endpoint at /health

Reload after config change:
```bash
sudo ./scripts/nginx-reload.sh
```

### WireGuard VPN

Server config: `/etc/wireguard/wg0.conf`

Generate keypair on server:
```bash
wg genkey | tee server_private.key | wg pubkey > server_public.key
```

Add a new client:
```bash
# On server: generate client pubkey
CLIENT_PUB=$(wg genkey | tee client_private.key | wg pubkey)
echo "$CLIENT_PUB"   # show it, then add to wg0.conf [Peer] block

# On client device: generate own keypair
wg genkey > client_private.key
wg pubkey < client_private.key   # send this to server admin
```

Client config template: `wireguard/client-wg0.conf`

### SSL / Let's Encrypt

First-time certificate issuance:
```bash
sudo certbot --nginx -d your-domain.com
```

Manual renewal check:
```bash
sudo ./scripts/cert-renew.sh          # live
sudo ./scripts/cert-renew.sh --dry-run # preview
```

Automatic renewal is handled by `certbot-renewal.timer` (runs at 03:00 and 15:00 daily, with up to 5 min random delay).

### systemd Units

| Unit | Type | Description |
|---|---|---|
| `certbot-renewal.timer` | timer | Triggers cert renewal twice daily |
| `certbot-renewal.service` | oneshot | Runs certbot renew with nginx reload hook |
| `deployment-manager.service` | oneshot | Runs your application deploy script |

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable certbot-renewal.timer
sudo systemctl start certbot-renewal.timer
```

---

## Security Notes

- `wg0.conf` has `chmod 600` — only root may read it
- Nginx uses TLS 1.2/1.3 only (no legacy protocol fallback)
- Rate limiting on `/auth/` is strict (5 req/min) to slow brute-force attacks
- `deployment-manager.service` uses `NoNewPrivileges=true` and `PrivateTmp=true`
- All helper scripts require root; non-root deploy user should be created for the app

---

## Troubleshooting

**Nginx fails config test:**
```bash
sudo nginx -t
```

**WireGuard won't start:**
```bash
sudo wg show   # no output = interface not up
sudo journalctl -u wg-quick@wg0 -n 50
```

**certbot renewal fails:**
```bash
sudo certbot renew --dry-run
sudo journalctl -u certbot-renewal -n 50
```

**Check what's listening:**
```bash
sudo ss -tlnp | grep -E ':(80|443|51820|8000|8080|9000)\b'
```
