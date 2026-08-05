# Task 01: 專案骨架與開發環境

## 目標

建立 FastAPI 專案結構、Docker Compose 配置，確保開發環境能正常啟動。

## 實作指引

1. 建立 FastAPI app（`app/main.py`）
2. 實作 `GET /health` 端點
3. `app/config.py` 使用 pydantic-settings 管理環境變數
4. Dockerfile（multi-stage build）
5. Docker Compose 啟動 app + PostgreSQL
6. 設定 structlog 結構化日誌
7. 設定 Alembic migration

## 相關檔案

- `app/main.py`, `app/config.py`, `Dockerfile`, `docker-compose.yml`

## 依賴關係

- 無（第一個 Task）

## 驗收標準

```bash
docker compose up -d
curl http://localhost:8000/health
# {"status": "healthy", "services": {"postgresql": "connected"}}
```
