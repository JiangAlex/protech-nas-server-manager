# Task 06: 狀態監控服務

## 目標

實作裝置健康檢查、狀態更新、離線偵測。

## 實作指引

1. 使用 APScheduler 定時執行健康檢查
2. NAS 健康檢查：SSH ping 或 HTTP endpoint
3. ESP32 健康檢查：heartbeat 超時判斷（裝置主動回報 last_seen_at）
4. 狀態更新邏輯：
   - 健康檢查成功 → status = online, 更新 last_seen_at
   - 超時未回應 → status = offline
5. 離線告警觸發（連續 N 次失敗後通知）
6. `GET /api/devices/{id}/status` 即時查詢

## 相關檔案

- `app/services/status_monitor.py`, `app/services/scheduler.py`

## 依賴關係

- Task 01, Task 02, Task 07（通知服務）

## 驗收標準

- 定時檢查裝置狀態，DB 中 status 正確更新
- 裝置離線超時後觸發通知
- Web UI Dashboard 顯示即時狀態
