"""Dashboard API endpoints (unauthenticated).

Provides a public /api/dashboard/metrics endpoint that returns
an aggregated metrics overview for all active devices — intended
for client-side health checks without requiring session auth.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.metrics_snapshot import MetricsSnapshot
from app.services.metrics_service import get_latest_metrics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class DeviceMetricsSummary:
    """Lightweight metrics summary for a single device."""

    def __init__(
        self,
        device_id: int,
        device_name: str,
        status: str,
        last_seen_at,
        cpu_percent: float | None = None,
        memory_percent: float | None = None,
        disk_percent: float | None = None,
    ):
        self.device_id = device_id
        self.device_name = device_name
        self.status = status
        self.last_seen_at = last_seen_at
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.disk_percent = disk_percent


@router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return latest metrics for all active devices without authentication.

    This endpoint is intentionally unauthenticated so that external monitoring
    tools (e.g. uptime monitors, health checks) can scrape it without needing
    a session or API key.
    """
    # Fetch all active devices
    stmt = select(Device).where(Device.is_active == True)
    result = await db.execute(stmt)
    devices = result.scalars().all()

    summaries = []
    for device in devices:
        snapshot = await get_latest_metrics(db, device.id)
        if snapshot:
            summary = DeviceMetricsSummary(
                device_id=device.id,
                device_name=device.name,
                status=device.status,
                last_seen_at=str(device.last_seen_at) if device.last_seen_at else None,
                cpu_percent=float(snapshot.cpu_percent),
                memory_percent=float(snapshot.memory_percent),
                disk_percent=float(snapshot.disk_percent),
            )
        else:
            summary = DeviceMetricsSummary(
                device_id=device.id,
                device_name=device.name,
                status=device.status,
                last_seen_at=str(device.last_seen_at) if device.last_seen_at else None,
            )
        summaries.append({
            "device_id": summary.device_id,
            "device_name": summary.device_name,
            "status": summary.status,
            "last_seen_at": summary.last_seen_at,
            "cpu_percent": summary.cpu_percent,
            "memory_percent": summary.memory_percent,
            "disk_percent": summary.disk_percent,
        })

    total = len(summaries)
    online = sum(1 for s in summaries if s["status"] == "online")
    offline = total - online

    return {
        "total_devices": total,
        "online_devices": online,
        "offline_devices": offline,
        "devices": summaries,
    }
