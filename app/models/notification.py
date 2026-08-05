"""Notification config ORM model.

Table: notification_configs
"""

from typing import Optional

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NotificationConfig(Base, TimestampMixin):
    """Notification channel configuration."""

    __tablename__ = "notification_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )  # telegram / line / discord
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict
    )  # token, chat_id, channel_id, etc.
    notify_on_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_failure: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_on_offline: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
