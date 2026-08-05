"""Firmware version ORM model.

Table: firmware_versions
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, BigInteger, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class FirmwareVersion(Base, TimestampMixin):
    """Firmware version record."""

    __tablename__ = "firmware_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("device_types.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    git_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    git_hash_short: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    version_display: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    changelog: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # File info
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Git info
    git_repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    git_branch: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Flags
    is_latest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_stable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    device_type: Mapped["DeviceType"] = relationship("DeviceType", back_populates="firmware_versions")
