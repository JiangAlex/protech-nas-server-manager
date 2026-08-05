# API 規格文檔

## 1. 基本資訊

- **Base URL**：`http://localhost:8000`
- **認證**：Web UI 使用 Session；API 使用 `X-API-Key` header；OTA 使用 `X-Device-Token`
- **回應格式**：JSON

## 2. 健康檢查

### GET /health

**Response 200:**
```json
{
  "status": "healthy",
  "services": {"postgresql": "connected"},
  "devices": {"total": 12, "online": 10, "offline": 2},
  "version": "0.1.0"
}
```

## 3. 裝置管理 API

### GET /api/devices

列出所有裝置。

**Query Parameters:**
- `device_type`: 過濾裝置類型
- `status`: 過濾狀態 (online/offline/updating/error)
- `page`, `page_size`

**Response 200:**
```json
{
  "devices": [
    {
      "id": "dev_001",
      "name": "NAS-Office-01",
      "device_type": "nas",
      "current_version": "v1.2.3-abc1234",
      "status": "online",
      "last_seen_at": "2026-08-05T10:00:00Z",
      "ip_address": "192.168.1.100"
    }
  ],
  "total": 12
}
```

### POST /api/devices

註冊新裝置。

**Request Body:**
```json
{
  "name": "NAS-Office-02",
  "device_type_id": "type_nas",
  "ip_address": "192.168.1.101",
  "ssh_host": "192.168.1.101",
  "ssh_port": 22,
  "ssh_user": "protech",
  "config": {}
}
```

### GET /api/devices/{device_id}

取得裝置詳情（含更新歷史）。

### PUT /api/devices/{device_id}

更新裝置設定。

### DELETE /api/devices/{device_id}

刪除裝置（軟刪除）。

## 4. 更新操作 API

### POST /api/devices/{device_id}/update

觸發裝置更新。

**Request Body:**
```json
{
  "target_version": "v1.3.0-def5678",
  "target_git_hash": "def5678abcdef1234567890abcdef1234567890ab"
}
```

**Response 202:**
```json
{
  "update_id": "upd_xyz789",
  "device_id": "dev_001",
  "from_version": "v1.2.3-abc1234",
  "to_version": "v1.3.0-def5678",
  "status": "in_progress",
  "started_at": "2026-08-05T10:30:00Z"
}
```

### POST /api/devices/{device_id}/rollback

回退到上一版本。

**Response 202:**
```json
{
  "update_id": "upd_roll01",
  "device_id": "dev_001",
  "from_version": "v1.3.0-def5678",
  "to_version": "v1.2.3-abc1234",
  "status": "in_progress"
}
```

### GET /api/devices/{device_id}/updates

取得裝置更新歷史。

**Response 200:**
```json
{
  "updates": [
    {
      "id": "upd_xyz789",
      "from_version": "v1.2.3-abc1234",
      "to_version": "v1.3.0-def5678",
      "status": "completed",
      "triggered_by": "admin",
      "started_at": "2026-08-05T10:30:00Z",
      "completed_at": "2026-08-05T10:32:15Z"
    }
  ]
}
```

## 5. 韌體管理 API

### POST /api/firmware/upload

上傳韌體檔案（ESP32 等）。

**Headers:** Content-Type: multipart/form-data

**Form Data:**
- `file`: .bin 韌體檔案
- `device_type_id`: 裝置類型
- `version`: 版本號（e.g., "v1.1.0"）
- `git_hash`: git commit hash
- `changelog`: 更新日誌
- `is_stable`: true/false

**Response 201:**
```json
{
  "id": "fw_abc123",
  "device_type": "esp32",
  "version_display": "v1.1.0-ghi9012",
  "file_size": 1048576,
  "checksum_sha256": "a1b2c3...",
  "is_latest": true
}
```

### GET /api/firmware

列出韌體版本。

**Query Parameters:**
- `device_type_id`: 過濾裝置類型
- `is_stable`: 過濾穩定版

### GET /firmware/{device_type}/{version}/firmware.bin

韌體下載端點（供裝置 OTA 使用）。

### DELETE /api/firmware/{firmware_id}

刪除韌體版本。

## 6. OTA API（供 ESP32 等裝置呼叫）

### GET /api/ota/{device_type}/check

裝置查詢是否有新版本。

**Headers:** X-Device-Token: {token}

**Query Parameters:**
- `current_version`: 裝置目前版本
- `device_id`: 裝置識別碼

**Response 200:**
```json
{
  "update_available": true,
  "version": "v1.1.0-ghi9012",
  "file_url": "/firmware/esp32/v1.1.0-ghi9012/firmware.bin",
  "file_size": 1048576,
  "checksum_sha256": "a1b2c3...",
  "changelog": "修復 WiFi 重連問題"
}
```

### POST /api/ota/{device_type}/report

裝置回報更新結果。

**Headers:** X-Device-Token: {token}

**Request Body:**
```json
{
  "device_id": "esp32-001",
  "version": "v1.1.0-ghi9012",
  "status": "success",
  "message": ""
}
```

## 7. 裝置類型 API

### GET /api/device-types

列出所有裝置類型。

### POST /api/device-types

新增裝置類型。

**Request Body:**
```json
{
  "name": "esp32-sensor",
  "display_name": "ESP32 Sensor Module",
  "update_method": "ota_http",
  "health_check_method": "heartbeat",
  "config": {
    "ota_check_interval_seconds": 3600
  }
}
```

## 8. 通知設定 API

### GET /api/notifications/config

取得通知設定。

### PUT /api/notifications/config

更新通知設定。

**Request Body:**
```json
{
  "telegram": {
    "is_active": true,
    "notify_on_update": true,
    "notify_on_failure": true,
    "notify_on_offline": true
  }
}
```

## 9. 系統狀態 API

### GET /api/system/status

**Response 200:**
```json
{
  "app": {"version": "0.1.0", "uptime": "3d 5h"},
  "database": {"status": "connected"},
  "devices_summary": {
    "total": 12,
    "online": 10,
    "offline": 2,
    "updating": 0
  }
}
```

## 10. 錯誤回應格式

```json
{
  "error": {
    "code": "DEVICE_NOT_FOUND",
    "message": "Device with id 'dev_xxx' not found"
  }
}
```
