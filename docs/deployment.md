# 部署指南

## 1. 前置需求

- Docker 24.0+
- Docker Compose v2.20+
- SSH Key（用於連線 NAS 設備）

## 2. 環境變數設定

```bash
cp .env.example .env
vim .env
```

**必要設定：**
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` - Web UI 登入
- `SESSION_SECRET_KEY` - Session 加密金鑰
- `DATABASE_URL` - PostgreSQL 連線字串

**通知設定（至少設定一個）：**
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_NOTIFY_CHAT_ID`
- `LINE_CHANNEL_SECRET` + `LINE_CHANNEL_ACCESS_TOKEN`
- `DISCORD_BOT_TOKEN` + `DISCORD_NOTIFY_CHANNEL_ID`

## 3. Docker Compose 部署

```bash
# 啟動服務
docker compose up -d

# 查看狀態
docker compose ps

# 查看日誌
docker compose logs -f app

# 健康檢查
curl http://localhost:8000/health
```

## 4. 資料庫初始化

```bash
# 執行 migration
docker compose exec app alembic upgrade head
```

## 5. SSH Key 設定（NAS 連線）

```bash
# 產生 SSH Key（如果還沒有）
ssh-keygen -t ed25519 -f ~/.ssh/nas_manager_key -N ""

# 將公鑰部署到各 NAS
ssh-copy-id -i ~/.ssh/nas_manager_key.pub protech@nas-01.local

# 將私鑰掛載到 container（docker-compose.yml 已設定）
# 或放入 server 的 /app/ssh_keys/ 目錄
```

## 6. 新增裝置

### 6.1 新增 NAS 裝置

透過 Web UI：
1. 登入 `/admin/`
2. 進入「裝置管理」→「新增裝置」
3. 選擇類型：NAS
4. 填寫：名稱、IP、SSH port、SSH user
5. 測試連線

或透過 API：
```bash
curl -X POST http://localhost:8000/api/devices \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "NAS-Office-01",
    "device_type_id": "nas",
    "ip_address": "192.168.1.100",
    "ssh_host": "192.168.1.100",
    "ssh_port": 22,
    "ssh_user": "protech"
  }'
```

### 6.2 新增 ESP32 裝置

ESP32 裝置通常自動註冊（首次呼叫 OTA check 時）：
```bash
# ESP32 首次啟動時呼叫
GET /api/ota/esp32/check?device_id=esp32-001&current_version=v0.0.0
```

## 7. 通知平台設定

### 7.1 Telegram

1. 搜尋 `@BotFather` 建立 Bot
2. 取得 Bot Token → 填入 `TELEGRAM_BOT_TOKEN`
3. 取得 Chat ID（群組或個人）→ 填入 `TELEGRAM_NOTIFY_CHAT_ID`

### 7.2 LINE

1. 建立 LINE Messaging API Channel
2. 取得 Channel Secret + Access Token

### 7.3 Discord

1. 建立 Discord Bot
2. 取得 Bot Token + 目標 Channel ID

## 8. 常見操作

### 推送 NAS 更新

```bash
# 透過 API
curl -X POST http://localhost:8000/api/devices/dev_001/update \
  -H "X-API-Key: your-key" \
  -d '{"target_version": "v1.3.0-def5678", "target_git_hash": "def5678..."}'
```

### 上傳 ESP32 韌體

```bash
curl -X POST http://localhost:8000/api/firmware/upload \
  -H "X-API-Key: your-key" \
  -F "file=@firmware.bin" \
  -F "device_type_id=esp32" \
  -F "version=v1.1.0" \
  -F "git_hash=ghi9012abcdef..." \
  -F "changelog=修復 WiFi 重連"
```

### Rollback

```bash
curl -X POST http://localhost:8000/api/devices/dev_001/rollback \
  -H "X-API-Key: your-key"
```

## 9. 備份

```bash
# PostgreSQL 備份
docker compose exec postgresql pg_dump -U nas_user nas_manager > backup_$(date +%Y%m%d).sql

# 韌體檔案備份
tar czf firmware_backup_$(date +%Y%m%d).tar.gz ./data/firmware/
```
