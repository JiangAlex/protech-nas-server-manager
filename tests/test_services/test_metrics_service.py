"""Tests for metrics_service — parsing logic and DB operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metrics_service import (
    collect_device_metrics,
    save_metrics_snapshot,
    get_latest_metrics,
    get_metrics_history,
)


# ── collect_device_metrics tests (HTTP/httpx) ─────────────────────────────────


@pytest.mark.asyncio
async def test_collect_device_metrics_no_api_base_url():
    """Device without api_base_url returns None without making any HTTP request."""
    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.api_base_url = None

    result = await collect_device_metrics(device)
    assert result is None


@pytest.mark.asyncio
async def test_collect_device_metrics_success():
    """Successfully collect metrics when HTTP endpoint returns valid JSON."""
    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.api_base_url = "http://192.168.1.100:8000"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "cpu": {"percent": 25.0},
        "memory": {"percent": 60.0},
        "disk": {"percent": 45.0},
        "network": {"bytes_recv_mb": 1.5, "bytes_sent_mb": 0.5},
        "temperatures": {
            "cpu_thermal_zone": {"current": 45000},
            "ambient": {"current": 32000},
        },
    }

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = mock_response

    with patch("app.services.metrics_service.httpx.AsyncClient", return_value=mock_client):
        result = await collect_device_metrics(device)

    assert result is not None
    assert "cpu_percent" in result
    assert "memory_percent" in result
    assert "disk_percent" in result
    assert "network_io" in result
    assert "temperature" in result
    assert "collected_at" in result
    assert result["cpu_percent"] == 25.0
    assert result["memory_percent"] == 60.0
    assert result["disk_percent"] == 45.0
    # network_io stores bytes (converted from MB)
    assert result["network_io"]["rx_bytes"] == round(1.5 * 1024 * 1024)
    assert result["network_io"]["tx_bytes"] == round(0.5 * 1024 * 1024)
    # Temperature — cpu label matches first
    assert result["temperature"]["cpu"] == 45.0


@pytest.mark.asyncio
async def test_collect_device_metrics_http_status_error():
    """HTTP 4xx/5xx response returns None and logs error."""
    import httpx

    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.api_base_url = "http://192.168.1.100:8000"

    mock_response = MagicMock()
    mock_response.status_code = 502
    mock_response.json.return_value = {}
    error_response = httpx.HTTPStatusError(
        "Bad Gateway",
        request=MagicMock(),
        response=mock_response,
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.side_effect = error_response

    with patch("app.services.metrics_service.httpx.AsyncClient", return_value=mock_client):
        result = await collect_device_metrics(device)

    assert result is None


@pytest.mark.asyncio
async def test_collect_device_metrics_timeout():
    """httpx.TimeoutException returns None and logs error."""
    import httpx

    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.api_base_url = "http://192.168.1.100:8000"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.side_effect = httpx.TimeoutException("Connection timeout")

    with patch("app.services.metrics_service.httpx.AsyncClient", return_value=mock_client):
        result = await collect_device_metrics(device)

    assert result is None


@pytest.mark.asyncio
async def test_collect_device_metrics_network_error():
    """OS-level network error (host unreachable, DNS) returns None."""
    device = MagicMock()
    device.id = 1
    device.name = "test-device"
    device.api_base_url = "http://192.168.1.100:8000"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.side_effect = OSError("Network is unreachable")

    with patch("app.services.metrics_service.httpx.AsyncClient", return_value=mock_client):
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
