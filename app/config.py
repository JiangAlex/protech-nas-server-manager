"""Application configuration using pydantic-settings.

Loads settings from environment variables:
- App: host, port, log_level, env
- Auth: admin_username, admin_password, session_secret_key
- Database: database_url, postgres_*
- SSH: default_port, default_user
- Update: git_branch, timeout, rollback_enabled
- Notification: telegram/line/discord tokens and targets
- Health check: interval_seconds
"""
