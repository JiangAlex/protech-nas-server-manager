# Task 03: 版本管理與韌體存儲

## 目標

建立版本管理系統（firmware_versions 表）和韌體檔案上傳/下載功能。

## 實作指引

1. SQLAlchemy model：`firmware_versions`
2. 版本格式：`v{major}.{minor}.{patch}-{git_hash_7}`
3. 韌體上傳 API：接收 .bin + version + git_hash → 計算 SHA256 → 存檔
4. 韌體下載端點：`GET /firmware/{device_type}/{version}/firmware.bin`
5. 版本列表 API：按 device_type 過濾，標記 is_latest
6. 檔案存放於 `./data/firmware/` 目錄

## 相關檔案

- `app/models/firmware.py`, `app/routers/firmware.py`, `app/services/firmware_service.py`

## 依賴關係

- Task 01, Task 02

## 驗收標準

```bash
# 上傳韌體
curl -X POST /api/firmware/upload -F "file=@test.bin" -F "version=v1.0.0" -F "git_hash=abc1234..."
# 下載韌體
curl /firmware/esp32/v1.0.0-abc1234/firmware.bin -o downloaded.bin
# SHA256 一致
```
