# 需求規格文檔

## 1. 功能需求

### 1.1 裝置管理

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-01 | 支援註冊/編輯/刪除/停用裝置 | P0 |
| FR-02 | 支援多種裝置類型（NAS, ESP32, 其他 FW） | P0 |
| FR-03 | 裝置類型可動態新增，無需改程式碼 | P0 |
| FR-04 | 每台裝置記錄 current version + git hash | P0 |
| FR-05 | 裝置狀態即時顯示（online/offline/updating/error） | P0 |
| FR-06 | 支援裝置分組/標籤 | P2 |

### 1.2 版本管理

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-10 | 版本格式：v{major}.{minor}.{patch}-{git_hash_7} | P0 |
| FR-11 | 記錄完整 git commit hash（40 字元） | P0 |
| FR-12 | 每個 device_type 有獨立的版本線 | P0 |
| FR-13 | 支援標記版本為 stable / beta / dev | P1 |
| FR-14 | 版本 changelog 記錄 | P1 |
| FR-15 | 版本比較和歷史查看 | P1 |

### 1.3 NAS 更新（SSH + Git）

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-20 | 透過 SSH 連線到 NAS 執行更新 | P0 |
| FR-21 | 更新流程：git fetch → git checkout {hash} → rebuild → restart | P0 |
| FR-22 | 支援指定更新到特定 version + git hash | P0 |
| FR-23 | 支援 rollback 到上一版本 | P0 |
| FR-24 | 更新過程即時顯示進度/日誌 | P1 |
| FR-25 | 更新 timeout 機制（可配置） | P0 |
| FR-26 | 批次更新多台 NAS | P1 |

### 1.4 ESP32 OTA 更新

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-30 | 管理員上傳 .bin 韌體檔案到 server | P0 |
| FR-31 | 記錄韌體 version + git hash + SHA256 checksum | P0 |
| FR-32 | ESP32 定時向 server 查詢是否有新版本 | P0 |
| FR-33 | 提供 firmware 下載端點供 ESP32 OTA | P0 |
| FR-34 | ESP32 更新完成後回報狀態 | P0 |
| FR-35 | 管理員可手動觸發 ESP32 更新（通知 ESP32 來拉取） | P1 |
| FR-36 | 韌體檔案 checksum 驗證 | P0 |

### 1.5 狀態監控

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-40 | NAS 定時健康檢查（SSH ping / HTTP） | P0 |
| FR-41 | ESP32 heartbeat 回報 | P0 |
| FR-42 | 裝置離線超時告警 | P0 |
| FR-43 | 顯示裝置最後上線時間 | P0 |
| FR-44 | 顯示裝置資源使用（CPU/RAM/Disk，NAS only） | P2 |

### 1.6 通知服務

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-50 | 更新成功時通知管理員 | P0 |
| FR-51 | 更新失敗時通知管理員 | P0 |
| FR-52 | 裝置離線時通知管理員 | P0 |
| FR-53 | 新版本上傳時通知管理員 | P1 |
| FR-54 | 支援 Telegram 通知 | P0 |
| FR-55 | 支援 LINE 通知 | P1 |
| FR-56 | 支援 Discord 通知 | P2 |
| FR-57 | 通知平台可動態啟用/停用 | P1 |

### 1.7 Web 管理介面

| ID | 需求 | 優先級 |
|----|------|--------|
| FR-60 | 管理員登入/登出 | P0 |
| FR-61 | Dashboard 顯示所有裝置狀態總覽 | P0 |
| FR-62 | 裝置列表（按類型過濾、狀態過濾） | P0 |
| FR-63 | 裝置詳情頁（版本、狀態、更新歷史、操作按鈕） | P0 |
| FR-64 | 韌體管理頁（上傳、版本列表、設定 latest） | P0 |
| FR-65 | 更新記錄頁（所有更新歷史、篩選） | P1 |
| FR-66 | 通知設定頁（各平台 token 設定、啟用/停用） | P1 |
| FR-67 | 裝置類型管理頁 | P1 |

## 2. 非功能需求

### 2.1 效能

| ID | 需求 | 標準 |
|----|------|------|
| NFR-01 | 裝置狀態更新延遲 | < 30 秒 |
| NFR-02 | OTA check API 回應時間 | < 200ms |
| NFR-03 | 支援裝置數量 | 20+ 台同時管理 |
| NFR-04 | 韌體下載速度 | 不低於 1MB/s |

### 2.2 可靠性

| ID | 需求 | 標準 |
|----|------|------|
| NFR-10 | 更新失敗自動通知 | 100% 覆蓋 |
| NFR-11 | 更新記錄不丟失 | 所有更新操作持久化 |
| NFR-12 | Rollback 機制 | NAS 更新失敗可回退 |
| NFR-13 | 服務自動重啟 | Docker restart: unless-stopped |

### 2.3 安全性

| ID | 需求 | 標準 |
|----|------|------|
| NFR-20 | SSH Key 不經 Web 傳輸 | Server 端存放 |
| NFR-21 | 韌體完整性 | SHA256 checksum 驗證 |
| NFR-22 | OTA API 認證 | Device token 驗證 |
| NFR-23 | Web UI 認證 | Session-based + bcrypt |
| NFR-24 | 密鑰管理 | .env 管理，不進 git |

## 3. OTA API 協議（ESP32）

### 3.1 版本查詢

```
GET /api/ota/{device_type}/check
Headers: X-Device-Token: {token}
Query: current_version=v1.0.0-def5678&device_id={id}

Response:
{
  "update_available": true,
  "version": "v1.1.0-ghi9012",
  "file_url": "/firmware/esp32/v1.1.0-ghi9012/firmware.bin",
  "file_size": 1048576,
  "checksum_sha256": "abc123...",
  "changelog": "修復 WiFi 重連問題"
}
```

### 3.2 更新回報

```
POST /api/ota/{device_type}/report
Headers: X-Device-Token: {token}
Body:
{
  "device_id": "esp32-001",
  "version": "v1.1.0-ghi9012",
  "status": "success",
  "message": ""
}
```

## 4. 使用者故事

### US-01：管理員更新 NAS

> 作為管理員，我想透過 Web 介面一鍵將 NAS-01 更新到最新版本。

**驗收標準**：
- 點擊更新按鈕，選擇目標版本（v1.2.3-abc1234）
- 系統透過 SSH 執行 git checkout + rebuild
- 更新完成後顯示成功，版本號更新
- 收到 Telegram 通知

### US-02：上傳 ESP32 韌體

> 作為管理員，我想上傳新的 ESP32 韌體，讓裝置自動更新。

**驗收標準**：
- 上傳 .bin 檔案，填寫版本號 + git hash
- 系統計算 SHA256 並存檔
- ESP32 下次 check 時發現新版本並下載更新
- 更新完成後 ESP32 回報成功

### US-03：裝置離線告警

> 作為管理員，我想在裝置離線時收到通知。

**驗收標準**：
- NAS-02 超過設定時間未回應健康檢查
- 系統透過 Telegram/LINE/Discord 發送離線告警
- Web UI 上裝置狀態顯示為 offline
