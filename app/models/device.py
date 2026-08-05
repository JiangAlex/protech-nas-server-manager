"""Device and DeviceType ORM models.

Tables:
- device_types: Defines device categories (nas, esp32, etc.)
- devices: Individual device instances
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DeviceType(Base, TimestampMixin):
    """Device category (nas, esp32, etc.)."""

    __tablename__ = "device_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    update_method: Mapped[str] = mapped_column(String(50), nullable=False, default="git_pull")
    health_check_method: Mapped[str] = mapped_column(String(50), nullable=False, default="http")
    config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Relationships
    devices: Mapped[list["Device"]] = relationship("Device", back_populates="device_type")
    firmware_versions: Mapped[list] = relationship("FirmwareVersion", back_populates="device_type")


class Device(Base, TimestampMixin):
    """Individual device instance."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("device_types.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Version info
    current_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    current_git_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    # Connection info
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    ssh_host: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    ssh_user: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Status
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_update_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="unknown", nullable=False)
    deploy_mode: Mapped[str] = mapped_column(String(20), default="systemd", nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Relationships
    device_type: Mapped["DeviceType"] = relationship("DeviceType", back_populates="devices")
    update_logs: Mapped[list] = relationship("UpdateLog", back_populates="device")
