"""Metrics API endpoints.

- GET /api/devices/{id}/metrics          — latest snapshot
- GET /api/devices/{id}/metrics/history — historical snapshots
- GET /api/devices/metrics/overview      — latest snapshot for all active devices
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.metrics_snapshot import MetricsSnapshot
from app.services import metrics_service


# ── Response schemas ─────────────────────────────────────────────────────────

class TemperatureResponse(BaseModel):
    cpu: float
    ambient: Optional[float] = None


class NetworkIOResponse(BaseModel):
    rx_bytes: int
    tx_bytes: int


class MetricsSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: NetworkIOResponse
    temperature: TemperatureResponse
    raw_json: Optional[dict] = None
    collected_at: datetime
    created_at: datetime
    updated_at: datetime


class MetricsOverviewItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: int
    device_name: str
    metrics: Optional[MetricsSnapshotResponse] = None


class MetricsOverviewResponse(BaseModel):
    devices: list[MetricsOverviewItem]


router = APIRouter(tags=["metrics"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_device_or_404(db: AsyncSession, device_id: int) -> Device:
    stmt = select(Device).where(Device.id == device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/api/devices/{device_id}/metrics", response_model=MetricsSnapshotResponse)
async def get_device_metrics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent metrics snapshot for a device."""
    await _get_device_or_404(db, device_id)
    snapshot = await metrics_service.get_latest_metrics(db, device_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No metrics found for this device")
    return snapshot


@router.post(
    "/api/devices/{device_id}/metrics/refresh",
    response_model=MetricsSnapshotResponse,
)
async def refresh_device_metrics(
    device_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Collect metrics from the device in real time via SSH, persist, and return.

    Unlike ``GET /metrics`` (which only reads the latest stored snapshot),
    this endpoint connects to the device on demand so the "health check"
    button reflects the current CPU / memory / disk state without waiting
    for the 5-minute scheduler cycle.
    """
    device = await _get_device_or_404(db, device_id)

    if not (device.ssh_host or device.ip_address) or not device.ssh_user:
        raise HTTPException(
            status_code=400,
            detail="Device has no SSH configuration (ssh_host/ip_address and ssh_user required)",
        )

    metrics = await metrics_service.collect_device_metrics(device)
    if metrics is None:
        raise HTTPException(
            status_code=502,
            detail="Failed to collect metrics from device via SSH",
        )

    snapshot = await metrics_service.save_metrics_snapshot(db, device_id, metrics)
    await db.flush()
    return snapshot


@router.get("/api/devices/{device_id}/metrics/history", response_model=list[MetricsSnapshotResponse])
async def get_device_metrics_history(
    device_id: int,
    hours: int = Query(24, ge=1, le=720, description="Number of hours of history to return"),
    db: AsyncSession = Depends(get_db),
):
    """Return metrics history for a device over the specified number of hours."""
    await _get_device_or_404(db, device_id)
    snapshots = await metrics_service.get_metrics_history(db, device_id, hours=hours)
    return snapshots


@router.get("/api/devices/metrics/overview", response_model=MetricsOverviewResponse)
async def get_metrics_overview(
    db: AsyncSession = Depends(get_db),
):
    """Return the latest metrics snapshot for every active device."""
    stmt = select(Device).where(Device.is_active == True)
    result = await db.execute(stmt)
    devices = result.scalars().all()

    items = []
    for device in devices:
        snapshot = await metrics_service.get_latest_metrics(db, device.id)
        items.append(
            MetricsOverviewItem(
                device_id=device.id,
                device_name=device.name,
                metrics=snapshot,
            )
        )

    return MetricsOverviewResponse(devices=items)
