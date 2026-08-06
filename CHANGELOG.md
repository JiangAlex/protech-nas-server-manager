# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- 韌體版本管理 API + Web 頁面
  - `GET /api/firmware` — 列出所有韌體版本（支援 device_type_id 篩選）
  - `POST /api/firmware` — 建立韌體版本記錄
  - `GET /api/firmware/{id}` — 取得韌體詳情
  - `PUT /api/firmware/{id}` — 更新韌體資訊
  - `DELETE /api/firmware/{id}` — 刪除韌體版本
  - `POST /api/firmware/{id}/latest` — 標記為 Latest
  - `POST /api/firmware/{id}/stable` — 標記為 Stable
  - `/admin/firmware/` — Web 管理頁面（列表 + 新增 modal + 操作按鈕）
- OTA 路由分離：NAS OTA 與 ESP32 OTA 獨立路由
  - `POST /api/ota/nas/check` — NAS 設備檢查新版本
  - `GET /api/ota/nas/download/{device_id}` — 取得 systemd 更新指令
  - `GET /api/ota/nas/artifacts/{version}/frontend.tar.gz` — 下載預建 frontend
  - `POST /api/ota/nas/artifacts/{version}/upload` — 上傳 frontend artifact
  - `POST /api/ota/nas/report` — NAS 回報更新結果
  - `GET /api/ota/esp32/check` — ESP32 檢查韌體（placeholder）
  - `GET /api/ota/esp32/firmware/{version}` — 下載 firmware.bin（placeholder）
  - `POST /api/ota/esp32/report` — ESP32 回報結果（placeholder）
- Device model 新增 `deploy_mode` 欄位（預設 `systemd`）
- FirmwareVersion model 新增 `frontend_artifact_path`、`frontend_checksum` 欄位
- Artifact storage service（上傳/下載/校驗 frontend.tar.gz）
- Alembic migration 002

### Removed
- 舊的統一 `/api/ota/*` 路由（已被 NAS/ESP32 分離路由取代）

---

## [0.1.0] - 2026-08-05

### Added
- 專案初始建立（FastAPI + Jinja2 + TailwindCSS 架構）
- Dockerfile 與 Docker Compose 部署配置（port 8060）
- PostgreSQL 整合（async SQLAlchemy + asyncpg）
  - 連線至外部 PG15（blog.softsnail.com:1432/NasServer）
  - Alembic async migration 支援
  - 初始 migration：device_types, devices, firmware_versions, update_logs, notification_configs
- ORM Models（DeviceType, Device, FirmwareVersion, UpdateLog, NotificationConfig）
- pydantic-settings 環境變數管理（app/config.py）
- 設備類型管理 API（GET/POST/PUT/DELETE `/api/device-types`）
- 設備管理 API（GET/POST/PUT/DELETE `/api/devices`，支援狀態/類型篩選）
- Web 管理介面
  - Session-based 認證（登入/登出）
  - Dashboard（設備狀態總覽卡片 + 設備列表）
  - 設備列表頁（新增 modal、篩選）
  - 設備詳情頁（基本資訊、SSH 連線、操作按鈕）
  - 設備類型管理頁（新增/刪除）
  - Base template（TailwindCSS + Alpine.js sidebar）
- Health check endpoint（GET `/health`）
- 專案文檔
  - README.md
  - docs/UserGuide.md
  - docs/architecture.md
  - docs/requirements.md
  - docs/api-spec.md
  - docs/deployment.md
  - docs/tasks/（9 個開發任務說明）

### Infrastructure
- GitHub repo：https://github.com/JiangAlex/protech-nas-server-manager
- Docker image 基於 python:3.11-slim
- 移除 docker-compose 內建 PostgreSQL，改用外部 PG15
