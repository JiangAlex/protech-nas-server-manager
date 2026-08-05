# Protech NAS Server Manager — 使用指南

## 目錄

1. [系統需求](#系統需求)
2. [安裝與部署](#安裝與部署)
3. [登入管理介面](#登入管理介面)
4. [設備類型管理](#設備類型管理)
5. [設備管理](#設備管理)
6. [REST API 使用](#rest-api-使用)
7. [資料庫管理](#資料庫管理)
8. [常見問題](#常見問題)

---

## 系統需求

| 項目 | 需求 |
|------|------|
| Docker | 20.10+ |
| Docker Compose | v2+ |
| PostgreSQL | 15+（外部已有） |
| Port | 8060（Web 管理介面） |

---

## 安裝與部署

### 1. 取得程式碼

```bash
git clone https://github.com/JiangAlex/protech-nas-server-manager.git
cd protech-nas-server-manager
```

### 2. 設定環境變數

```bash
cp .env.example .env
vim .env
```

主要需修改的設定：

```env
# 管理介面帳密
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-secure-password
SESSION_SECRET_KEY=your-random-secret-key

# PostgreSQL 連線
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/<database>

# 通知（選填，之後設定）
TELEGRAM_BOT_TOKEN=your-token
TELEGRAM_NOTIFY_CHAT_ID=your-chat-id
```

### 3. 建立資料庫

如果資料庫尚未建立：

```bash
psql -h <host> -p <port> -U <user> -d <existing_db> -c "CREATE DATABASE \"NasServer\";"
```

### 4. 啟動服務

```bash
docker compose up -d --build
```

### 5. 執行資料庫 Migration

```bash
docker exec -it nas-manager-app alembic upgrade head
```

### 6. 確認服務狀態

```bash
curl http://localhost:8060/health
# 預期回應: {"status":"ok"}
```

---

## 登入管理介面

1. 瀏覽器打開：`http://localhost:8060/admin/`
2. 輸入帳號密碼（`.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`）
3. 登入後進入 Dashboard

### 頁面導覽

| 頁面 | 路徑 | 說明 |
|------|------|------|
| Dashboard | `/admin/` | 設備狀態總覽 |
| 設備管理 | `/admin/devices/` | 設備列表、新增設備 |
| 設備詳情 | `/admin/devices/{id}/` | 單一設備資訊、操作 |
| 設備類型 | `/admin/device-types/` | 管理設備分類 |
| 韌體版本 | `/admin/firmware/` | 韌體管理（開發中） |
| 更新紀錄 | `/admin/updates/` | 更新歷史（開發中） |
| 通知設定 | `/admin/notifications/` | 通知通道設定（開發中） |

---

## 設備類型管理

設備類型定義了設備的分類和更新方式。**必須先建立設備類型，才能新增設備。**

### 透過 Web 介面

1. 進入 `/admin/device-types/`
2. 點擊「+ 新增類型」
3. 填入：
   - **名稱**：英文代碼（如 `nas`、`esp32`、`router`）
   - **顯示名稱**：中文描述（如「NAS 設備」）
   - **更新方式**：`Git Pull + Build` / `OTA` / `Docker Pull` / `手動`
   - **健康檢查**：`HTTP Ping` / `SSH` / `ICMP Ping` / `不檢查`

### 透過 API

```bash
curl -X POST http://localhost:8060/api/device-types \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nas",
    "display_name": "NAS 設備",
    "update_method": "git_pull",
    "health_check_method": "http"
  }'
```

---

## 設備管理

### 新增設備（Web）

1. 進入 `/admin/devices/`
2. 點擊「+ 新增設備」
3. 填入設備名稱、類型、IP、SSH 資訊
4. 點擊「新增」

### 新增設備（API）

```bash
curl -X POST http://localhost:8060/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "device_type_id": 1,
    "name": "NAS-Office-01",
    "ip_address": "192.168.1.101",
    "ssh_host": "192.168.1.101",
    "ssh_port": 22,
    "ssh_user": "protech",
    "description": "辦公室 NAS"
  }'
```

### 設備詳情頁

在設備詳情頁面可以查看：
- 基本資訊（名稱、IP、版本、狀態）
- SSH 連線資訊（含複製用的 SSH 指令）
- 操作按鈕（推送更新、Rollback、健康檢查）
- 時間戳記（建立時間、最後更新、最後上線）

---

## REST API 使用

### 基本資訊

- Base URL：`http://localhost:8060`
- API 文件（Swagger）：`http://localhost:8060/docs`
- API 文件（ReDoc）：`http://localhost:8060/redoc`

### Device Types API

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/device-types` | 列出所有設備類型 |
| POST | `/api/device-types` | 建立設備類型 |
| GET | `/api/device-types/{id}` | 取得單一設備類型 |
| PUT | `/api/device-types/{id}` | 更新設備類型 |
| DELETE | `/api/device-types/{id}` | 刪除設備類型 |

### Devices API

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/devices` | 列出所有設備 |
| POST | `/api/devices` | 新增設備 |
| GET | `/api/devices/{id}` | 取得設備詳情 |
| PUT | `/api/devices/{id}` | 更新設備資訊 |
| DELETE | `/api/devices/{id}` | 停用設備（軟刪除） |

### 篩選設備

```bash
# 依狀態篩選
curl "http://localhost:8060/api/devices?status=online"

# 依設備類型篩選
curl "http://localhost:8060/api/devices?device_type_id=1"

# 只看啟用中的設備
curl "http://localhost:8060/api/devices?is_active=true"
```

---

## 資料庫管理

### 執行 Migration

```bash
# 升級到最新版本
docker exec -it nas-manager-app alembic upgrade head

# 查看目前版本
docker exec -it nas-manager-app alembic current

# 查看 migration 歷史
docker exec -it nas-manager-app alembic history
```

### 資料庫連線資訊

```
Host: <your-db-host>
Port: <your-db-port>
User: <your-db-user>
Database: NasServer
```

### 資料表

| 表名 | 說明 |
|------|------|
| `device_types` | 設備類型定義 |
| `devices` | 設備實例 |
| `firmware_versions` | 韌體版本記錄 |
| `update_logs` | 更新操作紀錄 |
| `notification_configs` | 通知通道設定 |
| `alembic_version` | Migration 版本追蹤 |

---

## 常見問題

### Q: 容器啟動失敗，顯示 DB 連線錯誤？

確認 `.env` 中的 `DATABASE_URL` 正確，且 PostgreSQL 允許外部連線。測試：

```bash
psql -h <host> -p <port> -U <user> -d NasServer -c "SELECT 1;"
```

### Q: 忘記管理員密碼？

修改 `.env` 中的 `ADMIN_PASSWORD`，然後重啟容器：

```bash
docker compose restart app
```

### Q: 如何查看容器 log？

```bash
docker logs nas-manager-app --tail 50 -f
```

### Q: 如何更新程式碼？

```bash
git pull
docker compose up -d --build
```

### Q: Port 8060 被佔用？

修改 `docker-compose.yml` 中的 port mapping：

```yaml
ports:
  - "其他port:8000"
```

### Q: 如何備份資料庫？

```bash
pg_dump -h <host> -p <port> -U <user> NasServer > backup_$(date +%Y%m%d).sql
```

---

## 版本資訊

- **目前版本**：v0.1.0
- **Python**：3.11
- **FastAPI**：0.115.0
- **PostgreSQL**：15+
