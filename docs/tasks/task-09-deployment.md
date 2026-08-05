# Task 09: 部署與生產配置

## 目標

完善 Docker 生產配置、文檔、備份機制。

## 實作指引

1. Dockerfile（multi-stage, non-root user）
2. docker-compose.prod.yml（資源限制、log 配置）
3. Nginx reverse proxy + SSL
4. 備份腳本（PostgreSQL + firmware files）
5. SSH Key 管理流程文檔
6. 完整部署 README

## 相關檔案

- `Dockerfile`, `docker-compose.prod.yml`, `nginx/`, `scripts/backup.sh`

## 依賴關係

- Task 01 ~ Task 08

## 驗收標準

- `docker compose up` 一鍵啟動
- 全部功能正常運作
- 備份腳本可執行
