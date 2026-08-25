"""MetricsSnapshot ORM model.

Table: metrics_snapshots — stores periodic CPU/memory/disk/network/temperature snapshots per device.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, JSONB, TimestampMixin


class MetricsSnapshot(Base, TimestampMixin):
    """Periodic metrics snapshot for a device."""

    __tablename__ = "metrics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("devices.id"), nullable=False, index=True
    )

    # CPU
    cpu_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Memory
    memory_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Disk
    disk_percent: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)

    # Network I/O
    network_io: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"rx_bytes": int, "tx_bytes": int}

    # Temperature
    temperature: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # {"cpu": float, "ambient": float | null}

    # Raw command output stored as JSON for debugging
    raw_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # When this snapshot was collected on the DUT (may differ from created_at on server)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
