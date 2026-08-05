# Task 08: Web 管理介面

## 目標

建立 Jinja2 + TailwindCSS 管理後台，提供裝置管理、更新操作、狀態監控的 Web UI。

## 實作指引

1. FastAPI + Jinja2 模板渲染
2. TailwindCSS（CDN）+ Alpine.js + HTMX
3. Session-based 認證（登入/登出）
4. 頁面：
   - `/admin/login` - 登入
   - `/admin/` - Dashboard（裝置狀態總覽、最近更新）
   - `/admin/devices/` - 裝置列表（按類型/狀態過濾）
   - `/admin/devices/{id}/` - 裝置詳情 + 操作按鈕（更新/rollback）
   - `/admin/firmware/` - 韌體版本列表 + 上傳
   - `/admin/updates/` - 更新歷史記錄
   - `/admin/notifications/` - 通知設定
   - `/admin/device-types/` - 裝置類型管理
5. HTMX 局部更新（裝置狀態定時刷新）

## 相關檔案

- `app/routers/web.py`, `app/templates/`, `app/static/`

## 依賴關係

- Task 01 ~ Task 07

## 驗收標準

- 登入後看到 Dashboard，顯示所有裝置狀態
- 可在裝置詳情頁觸發更新/rollback
- 可上傳韌體
- 狀態自動刷新
