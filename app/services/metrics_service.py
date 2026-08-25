"""Metrics collection service — SSH-based DUT monitoring.

Uses asyncssh to connect to DUT devices and collect:
  - CPU %  (top -bn1)
  - Memory % (free)
  - Disk %  (df -h /)
  - Network I/O  (/proc/net/dev)
  - Temperature  (thermal_zone0)
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import asyncssh
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.metrics_snapshot import MetricsSnapshot

logger = structlog.get_logger()


# ── Pydantic-style snapshot dict (used for validation) ──────────────────────

CPU_RE = re.compile(r"Cpu\(s\):.*?([0-9.]+).*?%id")
MEM_RE = re.compile(r"Mem:\s+\S+\s+\S+\s+([0-9.]+)\s+([0-9.]+)")
DISK_RE = re.compile(r"/dev/\S+\s+[0-9.]+[KMGT]?\s+[0-9.]+[KMGT]?\s+[0-9.]+[KMGT]?\s+([0-9.]+)%")
NET_RE = re.compile(r"eth0:\s+(\d+)\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+\d+\s+(\d+)")


def parse_top_output(raw: str) -> float:
    m = CPU_RE.search(raw)
    if m:
        return 100.0 - float(m.group(1))
    return 0.0


def parse_free_output(raw: str) -> float:
    m = MEM_RE.search(raw)
    if m:
        total = float(m.group(1))
        available = float(m.group(2))
        if total > 0:
            return (1.0 - available / total) * 100.0
    return 0.0


def parse_df_output(raw: str) -> float:
    m = DISK_RE.search(raw)
    if m:
        return float(m.group(1))
    return 0.0


def parse_netdev_output(raw: str) -> dict[str, int]:
    m = NET_RE.search(raw)
    if m:
        return {"rx_bytes": int(m.group(1)), "tx_bytes": int(m.group(2))}
    return {"rx_bytes": 0, "tx_bytes": 0}


def parse_temp_output(raw: str) -> float:
    try:
        return float(raw.strip()) / 1000.0
    except (ValueError, TypeError):
        return 0.0


async def collect_device_metrics(device: Device) -> dict[str, Any] | None:
    """Connect to DUT via SSH and collect all metrics.

    Returns a dict with keys: cpu_percent, memory_percent, disk_percent,
    network_io (rx_bytes/tx_bytes), temperature (cpu/ambient), raw_json,
    collected_at (UTC datetime).

    Returns None if the device has no SSH configuration or connection fails.
    """
    ssh_host = device.ssh_host or device.ip_address
    if not ssh_host or not device.ssh_user:
        logger.warning("metrics_no_ssh_config", device_id=device.id, device_name=device.name)
        return None

    commands = {
        "top": "top -bn1 | head -5",
        "free": "free | grep Mem",
        "df": "df -h / | tail -1",
        "netdev": "cat /proc/net/dev | grep eth0",
        "temp": "cat /sys/class/thermal/thermal_zone0/temp",
    }

    results: dict[str, str] = {}

    try:
        async with asyncssh.connect(
            host=ssh_host,
            port=device.ssh_port,
            username=device.ssh_user,
            known_hosts=None,
            server_host_key_algs=["ssh-rsa", "rsa-sha2-256", "rsa-sha2-512"],
            client_host_key_algs=["ssh-rsa", "rsa-sha2-256", "rsa-sha2-512"],
        ) as conn:
            for key, cmd in commands.items():
                result = await conn.run(cmd, check=False)
                results[key] = result.stdout
        logger.debug("metrics_collected_via_ssh", device_id=device.id, device_name=device.name)
    except asyncssh.Error as e:
        logger.error("metrics_ssh_error", device_id=device.id, device_name=device.name, error=str(e))
        return None

    cpu_percent = round(parse_top_output(results.get("top", "")), 2)
    memory_percent = round(parse_free_output(results.get("free", "")), 2)
    disk_percent = round(parse_df_output(results.get("df", "")), 2)
    network_io = parse_netdev_output(results.get("netdev", ""))
    temp_cpu = round(parse_temp_output(results.get("temp", "")), 2)

    collected_at = datetime.now(timezone.utc)

    return {
        "cpu_percent": cpu_percent,
        "memory_percent": memory_percent,
        "disk_percent": disk_percent,
        "network_io": network_io,
        "temperature": {"cpu": temp_cpu, "ambient": None},
        "raw_json": results,
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
