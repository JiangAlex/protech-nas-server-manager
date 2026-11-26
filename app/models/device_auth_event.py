"""Device authentication audit log.

One row per noteworthy authentication event of a device endpoint: a token issued, a wrong or
missing token, a refused enrollment (MAC mismatch), an admin token reset, a request from a new IP.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceAuthEvent(Base):
    __tablename__ = "device_auth_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    # enrolled / ok_new_ip / token_invalid / token_missing / enroll_rejected / mac_change_ignored /
    # token_reset / unknown_device
    event: Mapped[str] = mapped_column(String(40), nullable=False)
    endpoint: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    mac: Mapped[Optional[str]] = mapped_column(String(17), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
