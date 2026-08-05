# Changelog

All notable changes to this project will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- OTA API 供 NAS 設備主動檢查/拉取更新
  - `POST /api/ota/check` — 設備檢查是否有新版本
  - `GET /api/ota/download/{device_id}` — 取得更新下載資訊與執行指令
  - `POST /api/ota/report` — 設備回報更新結果（成功/失敗/rollback）

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
