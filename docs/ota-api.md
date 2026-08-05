# OTA API 規格

NAS 設備主動連回 Server 檢查更新、取得下載資訊、回報更新結果。

## 流程概覽

```
┌─────────────┐                          ┌──────────────────┐
│  NAS 設備    │                          │  Server (:8060)  │
└──────┬──────┘                          └────────┬─────────┘
       │                                          │
       │  1. POST /api/ota/check                  │
       │  {device_id, current_version}            │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：是否有新版本                        │
       │←─────────────────────────────────────────│
       │                                          │
       │  2. GET /api/ota/download/{device_id}    │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：git repo / branch / 執行指令       │
       │←─────────────────────────────────────────│
       │                                          │
       │  (NAS 執行更新...)                        │
       │                                          │
       │  3. POST /api/ota/report                 │
       │  {device_id, to_version, status}         │
       │─────────────────────────────────────────→│
       │                                          │
       │  回應：確認收到                            │
       │←─────────────────────────────────────────│
```

---

## API Endpoints

### 1. 檢查更新

**`POST /api/ota/check`**

NAS 設備傳送目前版本資訊，Server 比對最新韌體版本回應是否需要更新。

#### Request Body

```json
{
  "device_id": 1,
  "current_version": "1.0.0",
  "current_git_hash": "abc1234d",
  "device_type": "nas"
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| device_id | int | ✅ | 設備 ID |
| current_version | string | 選填 | 目前版本號 |
| current_git_hash | string | 選填 | 目前 git commit hash |
| device_type | string | 選填 | 設備類型（device_id 未註冊時的 fallback） |

#### Response（有更新）

```json
{
  "update_available": true,
  "current_version": "1.0.0",
  "latest_version": "1.1.0",
  "latest_git_hash": "def5678e",
  "changelog": "修正 XXX 問題，新增 YYY 功能",
  "download_url": "/api/ota/download/1",
  "file_size": 1048576,
  "file_checksum": "sha256:abcdef...",
  "released_at": "2026-08-05T10:00:00Z"
}
```

#### Response（無更新）

```json
{
  "update_available": false,
  "current_version": "1.1.0",
  "latest_version": "1.1.0"
}
```

#### 副作用

- 更新設備的 `last_seen_at`、`status = "online"`
- 更新設備的 `current_version`、`current_git_hash`

---

### 2. 取得更新資訊

**`GET /api/ota/download/{device_id}`**

取得更新的詳細下載/執行資訊。

#### Response

```json
{
  "version": "1.1.0",
  "git_hash": "def5678e",
  "git_repo_url": "https://github.com/JiangAlex/nas-app.git",
  "git_branch": "main",
  "file_url": null,
  "file_checksum": "sha256:abcdef...",
  "instructions": "cd /app && git fetch origin main && git checkout def5678e && docker compose up -d --build"
}
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| version | string | 目標版本號 |
| git_hash | string | 目標 git commit |
| git_repo_url | string | Git repository URL |
| git_branch | string | Git branch |
| file_url | string | 檔案下載路徑（二進位更新用） |
| file_checksum | string | 檔案 SHA256 校驗碼 |
| instructions | string | NAS 端執行的 shell 指令 |

#### Error Response

```json
{
  "detail": "No update available for this device"
}
```
Status: `404`

---

### 3. 回報更新結果

**`POST /api/ota/report`**

NAS 設備完成更新（或失敗）後回報結果。

#### Request Body

```json
{
  "device_id": 1,
  "from_version": "1.0.0",
  "to_version": "1.1.0",
  "to_git_hash": "def5678e",
  "status": "completed",
  "error_message": null
}
```

| 欄位 | 類型 | 必填 | 說明 |
|------|------|------|------|
| device_id | int | ✅ | 設備 ID |
| from_version | string | 選填 | 更新前版本 |
| to_version | string | ✅ | 目標版本 |
| to_git_hash | string | 選填 | 目標 git hash |
| status | string | ✅ | `completed` / `failed` / `rolled_back` |
| error_message | string | 選填 | 失敗時的錯誤訊息 |

#### Response

```json
{
  "success": true,
  "message": "Update report recorded: completed"
}
```

#### 副作用

- 更新設備的 `last_seen_at`、`status = "online"`
- 若 status = `completed`：更新 `current_version`、`current_git_hash`、`last_update_at`
- 建立一筆 `update_logs` 記錄

---

## NAS 端實作範例

```bash
#!/bin/bash
# NAS 系統更新腳本

SERVER_URL="http://your-server:8060"
DEVICE_ID=1
CURRENT_VERSION=$(cat /app/VERSION 2>/dev/null || echo "unknown")

# 1. 檢查更新
RESPONSE=$(curl -s -X POST "$SERVER_URL/api/ota/check" \
  -H "Content-Type: application/json" \
  -d "{\"device_id\": $DEVICE_ID, \"current_version\": \"$CURRENT_VERSION\"}")

UPDATE_AVAILABLE=$(echo "$RESPONSE" | jq -r '.update_available')

if [ "$UPDATE_AVAILABLE" != "true" ]; then
  echo "已是最新版本"
  exit 0
fi

LATEST_VERSION=$(echo "$RESPONSE" | jq -r '.latest_version')
echo "發現新版本: $LATEST_VERSION"

# 2. 取得更新指令
DOWNLOAD_INFO=$(curl -s "$SERVER_URL/api/ota/download/$DEVICE_ID")
INSTRUCTIONS=$(echo "$DOWNLOAD_INFO" | jq -r '.instructions')

# 3. 執行更新
echo "執行更新..."
if eval "$INSTRUCTIONS"; then
  STATUS="completed"
  ERROR=""
else
  STATUS="failed"
  ERROR="Update command failed with exit code $?"
fi

# 4. 回報結果
curl -s -X POST "$SERVER_URL/api/ota/report" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": $DEVICE_ID,
    \"from_version\": \"$CURRENT_VERSION\",
    \"to_version\": \"$LATEST_VERSION\",
    \"status\": \"$STATUS\",
    \"error_message\": \"$ERROR\"
  }"

echo "更新完成: $STATUS"
```

---

## 注意事項

1. **Server 端需先上傳韌體版本**：透過管理介面或 API 建立 `firmware_versions` 記錄，標記 `is_latest=true` 和 `is_stable=true`
2. **Device 需先註冊**：透過管理介面或 API 建立設備記錄，取得 `device_id`
3. **網路可達性**：NAS 設備必須能連到 Server 的 port 8060
4. **未來規劃**：加入 `X-Device-Token` header 認證，避免未授權設備呼叫 API
