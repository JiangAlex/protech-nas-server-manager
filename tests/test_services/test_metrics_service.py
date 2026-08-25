"""Tests for metrics_service — parsing logic and DB operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metrics_service import (
    parse_top_output,
    parse_free_output,
    parse_df_output,
    parse_netdev_output,
    parse_temp_output,
    collect_device_metrics,
    save_metrics_snapshot,
    get_latest_metrics,
    get_metrics_history,
)


# ── Parse function tests ─────────────────────────────────────────────────────


class TestParseTopOutput:
    def test_idle(self):
        raw = "Cpu(s):  0.0%us,  0.0%sy,  0.0%ni,100.0%id,  0.0%wa,  0.0%hi,  0.0%si,  0.0%st"
        assert parse_top_output(raw) == 0.0

    def test_busy(self):
        raw = "Cpu(s): 25.0%us,  5.0%sy,  0.0%ni, 70.0%id,  0.0%wa,  0.0%hi,  0.0%si,  0.0%st"
        assert parse_top_output(raw) == 30.0

    def test_no_match(self):
        assert parse_top_output("") == 0.0
        assert parse_top_output("not cpu output") == 0.0


class TestParseFreeOutput:
    def test_normal(self):
        # Mem: total used free shared buff/cache available
        raw = "Mem:        8050844     123456     500000        980      7426388     6543210"
        result = parse_free_output(raw)
        assert 0.0 <= result <= 100.0

    def test_no_match(self):
        assert parse_free_output("") == 0.0
        assert parse_free_output("not free output") == 0.0


class TestParseDfOutput:
    def test_normal(self):
        raw = "/dev/root      29378604  12345678  15432926  45% /"
        assert parse_df_output(raw) == 45.0

    def test_no_match(self):
        assert parse_df_output("") == 0.0


class TestParseNetdevOutput:
    def test_normal(self):
        raw = "eth0: 12345678  54321   0    0    0     0     0     0  987654  12345"
        result = parse_netdev_output(raw)
        assert result == {"rx_bytes": 12345678, "tx_bytes": 987654}

    def test_no_match(self):
        assert parse_netdev_output("") == {"rx_bytes": 0, "tx_bytes": 0}
        assert parse_netdev_output("no eth0 here") == {"rx_bytes": 0, "tx_bytes": 0}


class TestParseTempOutput:
    def test_valid(self):
        assert parse_temp_output("45000") == 45.0
        assert parse_temp_output("38000") == 38.0

    def test_invalid(self):
        assert parse_temp_output("") == 0.0
        assert parse_temp_output("not_a_number") == 0.0


# ── collect_device_metrics tests ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_collect_device_metrics_no_ssh_config():
    """Device without ssh_host/ip or ssh_user returns None without connecting."""
    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.ssh_host = None
    device.ip_address = None
    device.ssh_user = None

    result = await collect_device_metrics(device)
    assert result is None


@pytest.mark.asyncio
async def test_collect_device_metrics_success():
    """Successfully collect metrics when SSH returns valid output."""
    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.ssh_host = "192.168.1.100"
    device.ip_address = "192.168.1.100"
    device.ssh_port = 22
    device.ssh_user = "admin"

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(
        side_effect=[
            MagicMock(stdout="Cpu(s):  0.0%us,  0.0%sy,  0.0%ni,100.0%id,  0.0%wa\n"),
            MagicMock(stdout="Mem:        8050844     123456     500000        980      7426388     6543210\n"),
            MagicMock(stdout="/dev/root      29378604  12345678  15432926  45% /\n"),
            MagicMock(stdout="eth0: 12345678  54321   0    0    0     0     0     0  987654  12345\n"),
            MagicMock(stdout="45000\n"),
        ]
    )

    with patch("app.services.metrics_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value.__aenter__.return_value = mock_conn
        result = await collect_device_metrics(device)

    assert result is not None
    assert "cpu_percent" in result
    assert "memory_percent" in result
    assert "disk_percent" in result
    assert "network_io" in result
    assert "temperature" in result
    assert "collected_at" in result
    # CPU should be ~0% from idle output
    assert result["cpu_percent"] == 0.0
    # Disk should be 45%
    assert result["disk_percent"] == 45.0
    # Network
    assert result["network_io"]["rx_bytes"] == 12345678
    assert result["network_io"]["tx_bytes"] == 987654
    # Temperature
    assert result["temperature"]["cpu"] == 45.0


@pytest.mark.asyncio
async def test_collect_device_metrics_ssh_error():
    """SSH connection failure returns None and logs error."""
    import asyncssh

    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.ssh_host = "192.168.1.100"
    device.ip_address = "192.168.1.100"
    device.ssh_port = 22
    device.ssh_user = "admin"

    with patch("app.services.metrics_service.asyncssh.connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value.__aenter__.side_effect = asyncssh.Error(1, "connection refused")
        result = await collect_device_metrics(device)

    assert result is None


# ── DB operation tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_save_and_get_latest_metrics(db_session):
    """save_metrics_snapshot writes and get_latest_metrics retrieves it."""
    from app.models.device import Device, DeviceType
    from app.models.metrics_snapshot import MetricsSnapshot
    from datetime import datetime, timezone

    # Setup: create device type + device
    dt = DeviceType(name="test-nas", display_name="Test NAS")
    db_session.add(dt)
    await db_session.flush()

    device = Device(
        device_type_id=dt.id,
        name="Metrics-DUT-1",
        ssh_host="192.168.1.10",
        ssh_user="root",
        ssh_port=22,
    )
    db_session.add(device)
    await db_session.flush()
    await db_session.refresh(device)

    # Save a snapshot
    metrics = {
        "cpu_percent": 25.5,
        "memory_percent": 60.0,
        "disk_percent": 45.0,
        "network_io": {"rx_bytes": 1000, "tx_bytes": 2000},
        "temperature": {"cpu": 50.0, "ambient": None},
        "raw_json": {"top": "output"},
        "collected_at": datetime.now(timezone.utc),
    }
    snapshot = await save_metrics_snapshot(db_session, device.id, metrics)
    await db_session.commit()

    # Retrieve
    latest = await get_latest_metrics(db_session, device.id)
    assert latest is not None
    assert latest.cpu_percent == 25.5
    assert latest.memory_percent == 60.0
    assert latest.disk_percent == 45.0
    assert latest.network_io == {"rx_bytes": 1000, "tx_bytes": 2000}
    assert latest.temperature == {"cpu": 50.0, "ambient": None}


@pytest.mark.asyncio
async def test_get_latest_metrics_none(db_session):
    """get_latest_metrics returns None when no snapshots exist."""
    result = await get_latest_metrics(db_session, 99999)
    assert result is None


@pytest.mark.asyncio
async def test_get_metrics_history(db_session):
    """get_metrics_history returns snapshots within the specified hour window."""
    from app.models.device import Device, DeviceType
    from app.models.metrics_snapshot import MetricsSnapshot
    from datetime import datetime, timedelta, timezone

    # Setup device
    dt = DeviceType(name="test-nas-2", display_name="Test NAS 2")
    db_session.add(dt)
    await db_session.flush()

    device = Device(
        device_type_id=dt.id,
        name="Metrics-DUT-2",
        ssh_host="192.168.1.11",
        ssh_user="root",
        ssh_port=22,
    )
    db_session.add(device)
    await db_session.flush()
    await db_session.refresh(device)

    now = datetime.now(timezone.utc)

    # Create snapshots: 1 recent, 2 old (>24h ago)
    for i, offset_minutes in enumerate([0, -30, -90, -1500]):  # 0m, 30m, 90m, 25h ago
        snap = MetricsSnapshot(
            device_id=device.id,
            cpu_percent=float(i * 10),
            memory_percent=float(i * 5),
            disk_percent=10.0,
            network_io={"rx_bytes": 100 * i, "tx_bytes": 200 * i},
            temperature={"cpu": 40.0 + i, "ambient": None},
            raw_json={},
            collected_at=now + timedelta(minutes=offset_minutes),
        )
        db_session.add(snap)
    await db_session.commit()

    # Last 2 hours → should get 3 snapshots (0m, -30m, -60m)
    history = await get_metrics_history(db_session, device.id, hours=2)
    assert len(history) == 3

    # Last 1 hour → should get 2 snapshots (0m, -30m)
    history = await get_metrics_history(db_session, device.id, hours=1)
    assert len(history) == 2

    # Non-existent device
    history = await get_metrics_history(db_session, 99999, hours=24)
    assert history == []
