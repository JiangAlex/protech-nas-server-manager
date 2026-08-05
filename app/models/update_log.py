"""Update log ORM model.

Table: update_logs
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UpdateLog(Base, TimestampMixin):
    """Record of an update operation."""

    __tablename__ = "update_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(Integer, ForeignKey("devices.id"), nullable=False)
    from_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_version: Mapped[str] = mapped_column(String(50), nullable=False)
    to_git_hash: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # pending / in_progress / completed / failed / rolled_back
    triggered_by: Mapped[str] = mapped_column(
        String(20), default="admin", nullable=False
    )  # admin / scheduler / device
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="update_logs")
