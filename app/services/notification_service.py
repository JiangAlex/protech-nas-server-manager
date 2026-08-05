"""Unified notification dispatch service.

Dispatches notifications to all active channels:
- Loads active notification_configs from DB
- Formats message based on event type
- Sends to each active channel concurrently

Event types:
- update_success: "✅ {device} 已更新至 {version}"
- update_failure: "❌ {device} 更新失敗：{error}"
- device_offline: "⚠️ {device} 已離線超過 {minutes} 分鐘"
- firmware_uploaded: "📦 {device_type} 新韌體 {version} 已上傳"
"""
