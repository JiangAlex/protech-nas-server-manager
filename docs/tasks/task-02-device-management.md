# Task 02: 裝置類型與裝置管理

## 目標

建立裝置類型（device_types）和裝置（devices）的資料模型與 CRUD API。

## 實作指引

1. SQLAlchemy models：`device_types`, `devices`
2. Alembic migration 建表
3. API 端點：
   - `GET/POST /api/device-types`
   - `GET/POST/PUT/DELETE /api/devices`
   - `GET /api/devices/{id}`
4. 預建裝置類型：nas（ssh_git）、esp32（ota_http）
5. 裝置狀態 enum：online / offline / updating / error

## 相關檔案

- `app/models/device.py`, `app/routers/devices.py`, `app/routers/device_types.py`

## 依賴關係

- Task 01

## 驗收標準

- CRUD API 正常運作
- 預設 device_types 已建立
- 能註冊新裝置並查詢
