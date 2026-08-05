# Task 07: 多通道通知服務

## 目標

實作 Telegram、LINE、Discord 通知服務，在更新/失敗/離線時通知管理員。

## 實作指引

1. 建立 `NotificationChannel` 抽象基類
2. 實作子類：
   - `TelegramNotifier` - 使用 python-telegram-bot 發送訊息
   - `LINENotifier` - 使用 line-bot-sdk push message
   - `DiscordNotifier` - 使用 discord.py 或 webhook
3. `NotificationService` 統一呼叫所有啟用的通道
4. 通知設定存於 PostgreSQL（`notification_configs` 表）
5. 通知模板：
   - ✅ 更新成功：`{device_name} 已更新至 {version}`
   - ❌ 更新失敗：`{device_name} 更新失敗：{error}`
   - ⚠️ 裝置離線：`{device_name} 已離線超過 {minutes} 分鐘`
   - 📦 新韌體：`{device_type} 新韌體 {version} 已上傳`
6. 管理 API：啟用/停用各平台、測試發送

## 相關檔案

- `app/notifications/base.py`, `app/notifications/telegram.py`
- `app/notifications/line.py`, `app/notifications/discord.py`
- `app/services/notification_service.py`

## 依賴關係

- Task 01

## 驗收標準

- 更新成功後收到 Telegram 通知
- 更新失敗後收到通知含錯誤訊息
- 可透過管理 API 停用/啟用各通道
- 測試發送功能正常
