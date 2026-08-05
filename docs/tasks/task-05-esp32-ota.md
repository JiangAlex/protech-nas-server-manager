# Task 05: ESP32 OTA 更新服務

## 目標

實作 ESP32 OTA 更新機制：版本查詢 API、韌體下載、更新回報。

## 實作指引

1. 實作 `ESP32Updater(DeviceUpdater)` 類
2. OTA Check API：`GET /api/ota/{device_type}/check`
   - 比較裝置 current_version 與 latest firmware_version
   - 回傳下載 URL + checksum
3. OTA Report API：`POST /api/ota/{device_type}/report`
   - 裝置回報更新成功/失敗
   - 更新 devices.current_version
4. Device Token 認證（`X-Device-Token` header）
5. 裝置首次呼叫時自動註冊（如果 device_id 不存在）
6. 管理員手動觸發通知 ESP32 更新（設定 flag，下次 check 時回應）

## 相關檔案

- `app/services/updaters/esp32_updater.py`, `app/routers/ota.py`

## 依賴關係

- Task 01, Task 02, Task 03

## 驗收標準

```bash
# ESP32 查詢新版本
GET /api/ota/esp32/check?current_version=v1.0.0-abc1234&device_id=esp32-001
# → {"update_available": true, "version": "v1.1.0-ghi9012", ...}

# ESP32 下載韌體 + flash + 回報成功
POST /api/ota/esp32/report {"device_id":"esp32-001","version":"v1.1.0-ghi9012","status":"success"}
```
