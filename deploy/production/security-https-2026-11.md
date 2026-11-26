# 部署:API 驗證、裝置 token、HTTPS(Redmine #147)

主機 B400A(Tailscale 100.124.174.114,區網 192.168.2.223)。所有指令都在 B400A 上執行。
程式碼:`~/Documents/GitHub/protech-nas-server-manager`(commit 9e6da94 起)。

分三部分,**依序做**。A 不依賴 B、C,可以先做。

- A. 部署新版 manager(API 驗證、/docs 關閉、裝置 token 過渡期)— 越快越好
- B. 路由器與 HTTPS(blog.softsnail.com → manager)
- C. 之後:NAS 改用 HTTPS 與 token、強制驗證、關閉公網 8060

---

## A. 部署新版 manager

### A1. 備份

```bash
cd ~/Documents/GitHub/protech-nas-server-manager
cp .env .env.bak-$(date +%Y%m%d)

# 資料庫:用 .env 的 PG* 設定。PGHOST 若為 host.docker.internal,請改成 127.0.0.1
set -a; . ./.env; set +a
docker run --rm --network host -e PGPASSWORD="$PGPASSWORD" postgres:15-alpine \
  pg_dump -h "${PGHOST/host.docker.internal/127.0.0.1}" -p "$PGPORT" -U "$PGUSER" -d "$PGDATABASE" \
  > ~/nas-manager-db-$(date +%Y%m%d).sql
ls -la ~/nas-manager-db-*.sql        # 不能是 0 bytes
```

### A2. 換掉預設金鑰,加上新設定

目前 `SESSION_SECRET_KEY` 是程式裡的預設值(公開在 GitHub),任何人都能用它簽出「已登入」的 cookie。

```bash
python3 -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_urlsafe(48)); print('ADMIN_API_KEY=' + secrets.token_urlsafe(32))"
```

編輯 `.env`:

- 把 `SESSION_SECRET_KEY=...` 換成上面印出的新值(換掉後,目前登入的人要重新登入)
- 加上:
  ```
  ADMIN_API_KEY=<上面印出的值>
  ENABLE_API_DOCS=false
  DEVICE_TOKEN_ENFORCE=false
  ```
- 建議:`ADMIN_PASSWORD` 改成 16 字以上(目前 8 字)

`ADMIN_API_KEY` 也要設到 GitHub(protech-nas 的 CI 上傳 artifact 會用到),見 A6。

### A3. 更新程式碼並建新映像

```bash
git pull --ff-only          # 應該快轉到 9e6da94 或更新
git log --oneline -1
docker compose build app
```

### A4. 資料庫 migration(用新映像,舊容器照常服務)

006 只新增欄位與資料表,舊版程式不受影響,所以先 migration 再換容器。

```bash
docker compose run --rm app alembic upgrade head
docker compose run --rm app alembic current      # 應顯示 006 (head)
```

### A5. 換成新容器並驗證

```bash
docker compose up -d app
sleep 5
docker logs nas-manager-app 2>&1 | grep -E "insecure_default|device_token_transition|database_connected"
```

預期:有 `database_connected` 和 `device_token_transition_mode`(過渡期提醒);**不應**有 `insecure_default_session_secret`。
若有 `insecure_default_admin_password`,表示 ADMIN_PASSWORD 還是預設值。

```bash
KEY=$(grep ^ADMIN_API_KEY= .env | cut -d= -f2-)
curl -s -o /dev/null -w "health      %{http_code} (200)\n" http://127.0.0.1:8060/health
curl -s -o /dev/null -w "no key      %{http_code} (401)\n" http://127.0.0.1:8060/api/devices
curl -s -o /dev/null -w "docs        %{http_code} (404)\n" http://127.0.0.1:8060/docs
curl -s -o /dev/null -w "with key    %{http_code} (200)\n" -H "X-API-Key: $KEY" http://127.0.0.1:8060/api/devices
curl -s -o /dev/null -w "public      %{http_code} (401)\n" http://blog.softsnail.com:8060/api/devices
```

再用瀏覽器登入 `http://blog.softsnail.com:8060/admin/`,打開任一設備:要能看到「裝置驗證」卡片(尚未發 Token)與「驗證記錄」。
現有 NAS 的 check 照常運作(過渡期),每次會在驗證記錄留下「未帶 Token」。

**還原**(有問題時):
```bash
git checkout 0573f4a && docker compose build app && docker compose up -d app
# 006 的欄位留著不影響舊版;要移除:先用新版映像 docker compose run --rm app alembic downgrade 005
cp .env.bak-<日期> .env
```

### A6. protech-nas 的 CI(GitHub Actions)

protech-nas 的 `build-and-upload.yml` 會上傳 frontend artifact、更新 /api/firmware,現在需要 X-API-Key。
修改已 commit 在本機 `~/projects/protech-nas`(a00f827),但目前的 gh token 沒有 `workflow` 權限,GitHub 拒絕推送。在開發 PC 上:

```bash
gh auth refresh -h github.com -s workflow          # 會開瀏覽器授權
cd ~/projects/protech-nas && gh auth setup-git && git push origin main
gh secret set OTA_ADMIN_API_KEY -R JiangAlex/protech-nas      # 貼上 ADMIN_API_KEY
```

---

## B. 路由器與 HTTPS

### B0. 前提:公網 80 埠要轉到 B400A

目前公網 1.34.59.237 的 80 與 4443 是**路由器自己的遠端管理頁面**(自簽憑證 gateway.example.com,2025-07-31 已過期),
所以 Let's Encrypt 驗證進不到 B400A。softsnail.com 的 DNS 在 Google / Squarespace,沒有 API,無法自動用 DNS 驗證。

在路由器:

1. 關閉 WAN 端的遠端管理(Remote management / 遠端管理),或把它改到不對外的埠(這本身也是安全問題)
2. 新增轉送:TCP 80 → 192.168.2.223:80
3. 確認 443、8060 仍轉到 192.168.2.223

驗證(從外部,例如手機網路):`curl -I http://blog.softsnail.com/` 應看到 `Server: nginx` 與 `301`,不再是 `307 ... :4443`。

### B1. 備份 nginx 設定

```bash
cd ~/Documents/UbuntuServer
cp docker-compose.yml docker-compose.yml.bak-$(date +%Y%m%d)
cp -r nginx/nginx-config nginx/nginx-config.bak-$(date +%Y%m%d)
```

### B2. nginx 加入 manager 的網路、掛載 /etc/letsencrypt

編輯 `~/Documents/UbuntuServer/docker-compose.yml` 的 `nginx` 服務。`networks:` 下原本是清單寫法 `- n8n_network`,
要改成下面的對照寫法(n8n 服務的 `networks:` 不用改):

```yaml
    volumes:
      # ...原有三行保留...
      - /etc/letsencrypt:/etc/letsencrypt:ro          # 新增:直接讀 certbot 的憑證,續期自動生效
    networks:
      n8n_network:
      nas_manager:                                    # 新增
        ipv4_address: 172.20.0.250                    # 固定 IP,給 manager 的 FORWARDED_ALLOW_IPS
```

檔案最下方的 `networks:` 加上(原有的 n8n_network 保留):

```yaml
  nas_manager:
    external: true
    name: protech-nas-server-manager_nas-manager-network
```

### B3. 先放 HTTP 驗證用的設定

新增 `~/Documents/UbuntuServer/nginx/nginx-config/conf.d/blog.softsnail.com.conf`:

```nginx
# HTTP: Let's Encrypt 驗證 + 轉 HTTPS
server {
    listen 80;
    server_name blog.softsnail.com;
    location /.well-known/acme-challenge/ { root /usr/share/nginx/html; }
    location / { return 301 https://$host$request_uri; }
}
```

n8n 的憑證也一起修(4 月已過期):`default.conf` 第一個 server(listen 80, n8n.softsnail.com)裡的
`return 301 https://$host$request_uri;` 改成:

```nginx
    location /.well-known/acme-challenge/ { root /usr/share/nginx/html; }
    location / { return 301 https://$host$request_uri; }
```

套用:

```bash
cd ~/Documents/UbuntuServer
docker compose up -d nginx                  # 重建 nginx(新的掛載與網路),n8n 不受影響
docker exec my-proxy-nginx nginx -t
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{$v.IPAddress}}  {{end}}' my-proxy-nginx
# 應包含 protech-nas-server-manager_nas-manager-network 172.20.0.250
```

### B4. 申請憑證

```bash
sudo certbot certonly --webroot -w /home/alex_chiang/Documents/UbuntuServer/nginx/html -d blog.softsnail.com
sudo certbot certonly --webroot -w /home/alex_chiang/Documents/UbuntuServer/nginx/html \
     -d n8n.softsnail.com --cert-name n8n.softsnail.com --force-renewal
sudo certbot certificates          # 兩張都要有,到期日約 90 天後
```

### B5. HTTPS 設定

在 `blog.softsnail.com.conf` 加上:

```nginx
server {
    listen 443 ssl;
    server_name blog.softsnail.com;
    ssl_certificate     /etc/letsencrypt/live/blog.softsnail.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/blog.softsnail.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    client_max_body_size 20m;                        # 韌體 / artifact 上傳

    location / {
        proxy_pass http://nas-manager-app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $remote_addr;   # 覆寫,不接受用戶端自己帶的值
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

n8n 的 443 server 改用新憑證:

```nginx
    ssl_certificate     /etc/letsencrypt/live/n8n.softsnail.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/n8n.softsnail.com/privkey.pem;
```

```bash
docker exec my-proxy-nginx nginx -t && docker exec my-proxy-nginx nginx -s reload
```

### B6. 續期後自動 reload

```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh >/dev/null <<'EOF'
#!/bin/sh
docker exec my-proxy-nginx nginx -s reload
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
sudo certbot renew --dry-run         # 兩張都要 success
```

### B7. manager 記錄真實的來源 IP

經 nginx 進來的請求,manager 看到的來源是 nginx(172.20.0.250)。讓 uvicorn 只信任 nginx 帶的 X-Forwarded-For:

```bash
cd ~/Documents/GitHub/protech-nas-server-manager
echo 'FORWARDED_ALLOW_IPS=172.20.0.250' >> .env
docker compose up -d app
```

### B8. 驗證

```bash
curl -s -o /dev/null -w "https health %{http_code} (200)\n" https://blog.softsnail.com/health
curl -s -o /dev/null -w "https api    %{http_code} (401)\n" https://blog.softsnail.com/api/devices
echo | openssl s_client -connect blog.softsnail.com:443 -servername blog.softsnail.com 2>/dev/null | openssl x509 -noout -subject -enddate
echo | openssl s_client -connect n8n.softsnail.com:443 -servername n8n.softsnail.com 2>/dev/null | openssl x509 -noout -subject -enddate
```

管理頁改用 `https://blog.softsnail.com/admin/`。

---

## C. 之後(NAS 端更新後)

1. protech-nas 的 `scripts/ota-update.sh` 與 `backend/src/services/system_service.py` 改成:
   check 時送 `"request_token": true` 與 MAC,把回應的 `device_token` 存檔(權限 600),之後每次帶 `X-Device-Token`;
   `OTA_SERVER_URL` 改成 `https://blog.softsnail.com`
2. 各 NAS 更新後,在設備頁確認「已發 Token」,驗證記錄沒有「Token 錯誤 / 拒絕發放 / 拒絕改 MAC」
3. 全部都有 token 後:`.env` 設 `DEVICE_TOKEN_ENFORCE=true`,`docker compose up -d app`
4. 關閉公網 8060:路由器移除 8060 的轉送(或 docker-compose 改成 `127.0.0.1:8060:8000`)

## 驗證記錄怎麼看

設備詳情頁的「驗證記錄」,或 `curl -H "X-API-Key: $KEY" http://127.0.0.1:8060/api/devices/<id>/auth-events`。

| 事件 | 意思 | 要注意 |
|---|---|---|
| 發放 Token(enrolled) | 裝置第一次 check 拿到 token | 時間、IP 是否為那台 NAS |
| 新 IP(ok_new_ip) | 有效 token 從新的 IP 來 | NAS 搬家或換網路是正常;不認得的 IP 要查 |
| 未帶 Token(token_missing) | 過渡期的舊版 client | NAS 更新後應消失 |
| Token 錯誤(token_invalid) | 帶了錯的 token,已拒絕 | **可能有人冒用** |
| 拒絕發放(enroll_rejected) | 已有 token 或 MAC 不符,不發新的 | **可能有人冒用**;若是真的換機,用「重設 Token」 |
| 拒絕改 MAC(mac_change_ignored) | 沒有有效 token 卻想改 MAC | **可能有人冒用** |
| 管理員重設(token_reset) | 管理頁按了重設 | |
| 未知裝置(unknown_device) | 不存在的 device_id | 大量出現代表有人在掃 |

---

## D. ESP32 OTA(manager 端,commit 之後的版本)

步驟同 A3 到 A5:

```bash
cd ~/Documents/GitHub/protech-nas-server-manager
git pull --ff-only
docker compose build app
docker compose run --rm app alembic upgrade head      # 007 (head):firmware_versions.file_signature
docker compose up -d app
```

選用:讓伺服器在上傳時就驗簽(發布流程出錯能及早發現)。公鑰放在 artifacts volume 裡:

```bash
docker cp fw_signing_pub.pem nas-manager-app:/app/data/artifacts/fw_signing_pub.pem
echo 'FIRMWARE_PUBLIC_KEY_FILE=/app/data/artifacts/fw_signing_pub.pem' >> .env
docker compose up -d app
```

登記 ESP32 設備(方式 a:管理員先建,板子第一次 check 才發 token):

1. 設備類型:新增一個 ESP32 用的類型(例如 name `lcd2`、update_method `ota_http`)
2. 設備:選這個類型,MAC 填板子的 Wi-Fi MAC(序列埠或燒錄時 esptool 顯示的 MAC)
