"""Notification config ORM model.

Table: notification_configs
Columns: id, platform (telegram/line/discord), is_active,
         config (JSON: token, chat_id, channel_id, etc.),
         notify_on_update, notify_on_failure, notify_on_offline
"""
