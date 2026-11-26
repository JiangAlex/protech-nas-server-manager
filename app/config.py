"""Application configuration using pydantic-settings.

Loads settings from environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "info"

    # Auth
    admin_username: str = "admin"
    admin_password: str = "change-me-in-production"
    session_secret_key: str = "change-this-to-a-random-secret-key"
    # X-API-Key for scripts calling the admin API (empty = only the web login session is accepted)
    admin_api_key: str = ""
    # /docs, /redoc and /openapi.json (off by default: the server is reachable from the internet)
    enable_api_docs: bool = False
    # Device tokens (X-Device-Token) on the device endpoints. False = transition: a missing token is
    # logged and allowed; a wrong token is always rejected. True = a missing token is rejected too.
    device_token_enforce: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://nas_user:nas_password@localhost:5432/nas_manager"

    # SSH defaults
    nas_ssh_default_port: int = 22
    nas_ssh_default_user: str = "protech"

    # Update
    update_git_branch: str = "main"
    update_timeout_seconds: int = 300
    update_rollback_enabled: bool = True

    # Health check
    nas_health_check_interval_seconds: int = 60

    # Telegram
    telegram_bot_token: str = ""
    telegram_notify_chat_id: str = ""

    # LINE
    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    line_notify_user_id: str = ""

    # Discord
    discord_bot_token: str = ""
    discord_notify_channel_id: str = ""

    # Docker
    docker_socket: str = "/var/run/docker.sock"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
