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
16. **Endpoints**
    - `POST /api/ota/check` — 設備檢查新版本
    - `GET /api/ota/download/{device_id}` — 取得更新指令
    - `POST /api/ota/report` — 設備回報更新結果
17. **Service Logic** — 版本比對、下載資訊生成、update_logs 記錄

### 文件

18. `docs/UserGuide.md` — 使用指南
19. `docs/ota-api.md` — OTA API 規格
20. `CHANGELOG.md` — 變更記錄

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
