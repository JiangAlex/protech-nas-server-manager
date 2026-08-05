# Task 04: NAS 更新服務（SSH + Git）

## 目標

實作透過 SSH 連線到 NAS 執行 git-based 更新的服務。

## 實作指引

1. 使用 `asyncssh` 建立 SSH 連線
2. 實作 `NASUpdater(DeviceUpdater)` 類
3. 更新流程：
   - SSH 連線 → `git fetch origin`
   - `git checkout {target_git_hash}`
   - `docker compose build && docker compose up -d`（或自定義 rebuild 指令）
4. 記錄更新日誌到 `update_logs` 表
5. 更新 `devices.current_version` 和 `current_git_hash`
6. Timeout 機制（可配置，預設 300s）
7. 失敗時自動 rollback（可選）

## 相關檔案

- `app/services/updaters/base.py`, `app/services/updaters/nas_updater.py`
- `app/routers/updates.py`

## 依賴關係

- Task 01, Task 02

## 驗收標準

- 透過 API 觸發 NAS 更新
- SSH 連線成功，git checkout 到指定 hash
- update_logs 記錄完整（from/to version, status, duration）
- 失敗時 status = failed，記錄 error_message
