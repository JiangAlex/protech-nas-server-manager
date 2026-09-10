"""Metrics collection service — HTTP-based DUT monitoring (phase 1, no auth).

Calls the client's unauthenticated GET /api/dashboard/metrics endpoint and maps:
  - cpu.percent          → cpu_percent
  - memory.percent       → memory_percent
  - disk.percent         → disk_percent
  - network.bytes_recv_mb / bytes_sent_mb → network_io (bytes)
  - temperatures.<label>.current           → temperature (cpu)
"""

import httpx
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.metrics_snapshot import MetricsSnapshot

logger = structlog.get_logger()


def _find_cpu_temperature(temperatures: dict) -> float:
    """Pick the first temperature label containing 'cpu' (case-insensitive).

    The client reports temperatures in milli-degrees (e.g. 45000 = 45.0 °C).
    This helper converts to degrees before returning.

    Returns 0.0 if no CPU-related label is found.
    """
    if not temperatures:
        return 0.0
    for label, entry in temperatures.items():
        if "cpu" in label.lower():
            try:
                return round(float(entry["current"]) / 1000.0, 2)
            except (TypeError, ValueError):
                continue
    # Fallback: return the first entry's current value (in degrees)
    first = next(iter(temperatures.values()), None)
    if first:
        try:
            return round(float(first["current"]) / 1000.0, 2)
        except (TypeError, ValueError):
            pass
    return 0.0


async def collect_device_metrics(device: Device) -> dict[str, Any] | None:
    """Call the DUT's unauthenticated /api/dashboard/metrics endpoint via HTTP.

    Returns a dict with keys: cpu_percent, memory_percent, disk_percent,
    network_io (rx_bytes/tx_bytes), temperature (cpu/ambient), raw_json,
    collected_at (UTC datetime).

    Returns None if api_base_url is not set or the HTTP request fails.
    """
    if not device.api_base_url:
        logger.warning("metrics_no_api_base_url", device_id=device.id, device_name=device.name)
        return None

    url = f"{device.api_base_url.rstrip('/')}/api/dashboard/metrics"
    timeout = httpx.Timeout(10.0, connect=5.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "metrics_http_status_error",
            device_id=device.id,
            device_name=device.name,
            url=url,
            status_code=e.response.status_code,
            error=str(e),
        )
        return None
    except (httpx.HTTPError, httpx.TimeoutException, OSError) as e:
        # httpx.HTTPError: network/connection errors
        # httpx.TimeoutException: connect or read timeout
        # OSError: host unreachable, DNS failure
        logger.error(
            "metrics_http_error",
            device_id=device.id,
            device_name=device.name,
            url=url,
            error=str(e),
            error_type=type(e).__name__,
        )
        return None

    logger.debug("metrics_collected_via_http", device_id=device.id, device_name=device.name)

    # Map client JSON → snapshot fields
    network = data.get("network", {})
    rx_mb = network.get("bytes_recv_mb", 0.0)
    tx_mb = network.get("bytes_sent_mb", 0.0)

    temperatures = data.get("temperatures", {})
    temp_cpu = _find_cpu_temperature(temperatures)

    collected_at = datetime.now(timezone.utc)

    return {
        "cpu_percent": round(float(data.get("cpu", {}).get("percent", 0.0)), 2),
        "memory_percent": round(float(data.get("memory", {}).get("percent", 0.0)), 2),
        "disk_percent": round(float(data.get("disk", {}).get("percent", 0.0)), 2),
        "network_io": {
            "rx_bytes": round(rx_mb * 1024 * 1024),
            "tx_bytes": round(tx_mb * 1024 * 1024),
        },
        "temperature": {"cpu": temp_cpu, "ambient": None},
        "raw_json": data,
        "collected_at": collected_at,
    }


async def save_metrics_snapshot(
    db: AsyncSession, device_id: int, metrics: dict[str, Any]
) -> MetricsSnapshot:
    """Write a metrics snapshot to the database."""
    snapshot = MetricsSnapshot(
        device_id=device_id,
        cpu_percent=metrics["cpu_percent"],
        memory_percent=metrics["memory_percent"],
        disk_percent=metrics["disk_percent"],
        network_io=metrics["network_io"],
        temperature=metrics["temperature"],
        raw_json=metrics.get("raw_json"),
        collected_at=metrics["collected_at"],
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


async def get_latest_metrics(db: AsyncSession, device_id: int) -> MetricsSnapshot | None:
    """Return the most recent metrics snapshot for a device."""
    stmt = (
        select(MetricsSnapshot)
        .where(MetricsSnapshot.device_id == device_id)
        .order_by(MetricsSnapshot.collected_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_metrics_history(
    db: AsyncSession, device_id: int, hours: int = 24
) -> list[MetricsSnapshot]:
    """Return all metrics snapshots for a device within the last N hours."""
    cutoff = datetime.now(timezone.utc).replace(microsecond=0)
    # subtract hours
    from datetime import timedelta
    cutoff = cutoff - timedelta(hours=hours)

    stmt = (
        select(MetricsSnapshot)
        .where(
            MetricsSnapshot.device_id == device_id,
            MetricsSnapshot.collected_at >= cutoff,
        )
        .order_by(MetricsSnapshot.collected_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())
