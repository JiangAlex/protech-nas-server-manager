# 開發記錄 (Memory)

記錄本專案每次開發的重要決策、修改、問題排除過程。

---

## 2026-08-05（三）

### 專案初始化與部署

1. **Git 初始化**
   - 建立 `.gitignore`（Python/Docker/Node 排除規則）
   - 首次 commit 64 個檔案推送到 GitHub
   - Repo: https://github.com/JiangAlex/protech-nas-server-manager

2. **Dockerfile 建立與修正**
   - 問題：缺少 Dockerfile → 建立 `python:3.11-slim` based image
   - 問題：`pip install .` 時缺少 source code → 改為先 COPY app/ 再 install
   - 問題：hatchling 找不到 package 目錄 → 在 `pyproject.toml` 加 `[tool.hatch.build.targets.wheel] packages = ["app"]`
   - 問題：`alembic.ini` 沒被 COPY 進 image → 加入 Dockerfile

3. **Docker Compose 調整**
   - Port 改為 `8060:8000`（原 8000 改 8060 對外）
   - 移除內建 PostgreSQL container，改用外部既有 PG15
   - 加入 `extra_hosts: host.docker.internal:host-gateway`

4. **PostgreSQL 連線**
   - 外部 PG15 位於 `blog.softsnail.com:1432`
   - Database: `NasServer`（從 `twsestock` DB 下 `CREATE DATABASE "NasServer"`）
   - `pg_hba.conf` 已有 `host all all all scram-sha-256`，允許所有 IP 連線

### PostgreSQL 整合

5. **app/config.py** — pydantic-settings 載入環境變數
6. **app/database.py** — async SQLAlchemy engine + session factory
7. **ORM Models** — DeviceType, Device, FirmwareVersion, UpdateLog, NotificationConfig
8. **Alembic** — async migration 支援，初始 migration 001 建立 5 張表
9. **main.py** — lifespan events（startup 測試 DB 連線，shutdown dispose engine）

### 設備管理 API + Web 管理介面

10. **Pydantic Schemas** — DeviceType/Device 的 Create/Update/Response
11. **Service Layer** — `device_service.py` 完整 CRUD
12. **API Routers**
    - `GET/POST/PUT/DELETE /api/device-types`
    - `GET/POST/PUT/DELETE /api/devices`（支援 status/type/active 篩選）
13. **Web Admin**
    - Session-based 認證（SessionMiddleware）
    - `/admin/login` — 登入頁
    - `/admin/` — Dashboard（狀態卡片 + 設備列表）
    - `/admin/devices/` — 設備列表 + 新增 modal
    - `/admin/devices/{id}/` — 設備詳情 + SSH 資訊 + 操作按鈕
    - `/admin/device-types/` — 設備類型管理
14. **Templates** — TailwindCSS CDN + Alpine.js sidebar + HTMX

### OTA API

15. **設計決策**：NAS 主動連回 Server 拉取更新（而非 Server SSH 推送）
16. **路由分離**：NAS OTA 與 ESP32 OTA 獨立路由
    - `/api/ota/nas/*` — NAS 設備（systemd 部署）
    - `/api/ota/esp32/*` — ESP32 設備（firmware binary，placeholder）
17. **NAS OTA Endpoints**
    - `POST /api/ota/nas/check` — 設備檢查新版本
    - `GET /api/ota/nas/download/{device_id}` — 取得 systemd 更新指令
    - `GET /api/ota/nas/artifacts/{version}/frontend.tar.gz` — 下載預建 frontend
    - `POST /api/ota/nas/artifacts/{version}/upload` — 上傳 frontend artifact（CI/admin）
    - `POST /api/ota/nas/report` — 設備回報更新結果
18. **deploy_mode 設計**
    - Device model 新增 `deploy_mode` 欄位（預設 `systemd`）
    - Systemd 模式：git pull + pip install + restart service + 下載預建 frontend artifact
    - Docker 模式：git pull + docker compose up --build（frontend 在 image 內 build）
    - NAS 硬體為 Atom D2550 / 4GB RAM，適合 systemd 直接運行
19. **Frontend Artifact 機制**
    - NAS 不需要安裝 Node.js
    - Server 端（或 CI）預建 frontend，打包為 `frontend.tar.gz`
    - NAS 只需下載解壓至 web 目錄
    - SHA256 checksum 校驗確保完整性
    - 存放於 Docker volume `artifacts_data` → `/app/data/artifacts/{version}/`
20. **Alembic Migration 002** — 新增 `devices.deploy_mode`、`firmware_versions.frontend_artifact_path`、`firmware_versions.frontend_checksum`
21. **設計建議記錄於 docs/ota-api.md**
    - Artifact 存放策略（目錄結構 + 版本清理）
    - 更新鎖機制（避免重複觸發）
    - Rollback 策略（symlink 切換 + 只保留前一版）
    - 漸進式更新 Canary Deploy（分階段 rollout）
    - 安全認證 `X-Device-Token`（未來實作）

### 文件

18. `docs/UserGuide.md` — 使用指南
19. `docs/ota-api.md` — OTA API 規格
20. `CHANGELOG.md` — 變更記錄

---

## 2026-08-06（四）

### 韌體版本管理

1. **Firmware API** — 完整 CRUD + mark latest/stable
   - `GET/POST/PUT/DELETE /api/firmware`
   - `POST /api/firmware/{id}/latest` — 標記為最新版（自動取消同類型其他版本的 latest）
   - `POST /api/firmware/{id}/stable` — 標記為穩定版
2. **Firmware Web 頁面** — `/admin/firmware/`
   - 版本列表（版本號、設備類型、git hash、branch、latest/stable 標記）
   - 新增版本 modal（version、device_type、git info、changelog、latest/stable flags）
   - 操作按鈕（設為 Latest、設為 Stable、刪除）
3. **Firmware Service** — 自動產生 `version_display`（如 `1.0.0-abc1234`），建立時若標記 latest 會自動取消前一個 latest

### OTA 更新判斷修正

4. **Git hash 比對** — OTA check 不再只比版本號，加上 git hash 比對
   - 版本相同 + hash 相同 → `update_available: false`
   - 版本不同 或 hash 不同 → `update_available: true`
   - 支援 short hash matching

### Device Model 擴充 & 群發更新

5. **Device 新增欄位**
   - `sku` — 設備 SKU 型號
   - `customer_id` — 客戶 ID
   - `mac_address` — MAC 地址
6. **Schemas 更新** — DeviceCreate/Update/Response 新增三個欄位
7. **NAS OTA** — NASCheckRequest 新增 `mac_address`，check_update 時保存 mac_address
8. **群發更新 API** — 新建 `app/routers/ota_batch.py`，支援批次推送更新
9. **Alembic Migration 003** — 新增 sku、customer_id、mac_address 欄位

| 檔案 | 變更 |
|------|------|
| `app/models/device.py` | Device 新增 sku、customer_id、mac_address 欄位 |
| `app/schemas/__init__.py` | DeviceCreate/Update/Response 新增三個欄位 |
| `app/schemas/ota_nas.py` | NASCheckRequest 新增 mac_address |
| `app/services/ota_nas_service.py` | check_update 時保存 mac_address |
| `app/routers/ota_batch.py` | 新建 — 群發更新 API |
| `app/main.py` | 註冊 ota_batch_router |
| `alembic/versions/003_add_sku_customer_mac.py` | 新建 — DB migration |

### 安全修正

21. 移除所有檔案中的真實帳密（`.env.example`、`alembic.ini`、`UserGuide.md`）
22. 敏感資訊僅保留在 `.env`（已被 `.gitignore` 排除）

---

## 待辦 / 未來規劃

- [ ] OTA API 加入 `X-Device-Token` 認證
- [ ] 韌體版本管理頁面（上傳/管理）
- [ ] 更新紀錄頁面
- [ ] 通知系統（Telegram/LINE/Discord）
- [ ] 狀態監控（定時健康檢查）
- [ ] NAS 端更新腳本整合
