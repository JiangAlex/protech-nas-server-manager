"""Tests for metrics router endpoints."""

import pytest
from httpx import AsyncClient


async def _create_device_type(client: AsyncClient) -> int:
    """Helper: create a device type and return its ID."""
    resp = await client.post(
        "/api/device-types",
        json={"name": "NAS-Metrics", "display_name": "NAS Metrics Test"},
    )
    return resp.json()["id"]


async def _create_device(client: AsyncClient, device_type_id: int, **overrides) -> dict:
    """Helper: create a device and return the response JSON."""
    payload = {
        "device_type_id": device_type_id,
        "name": "Test-Device",
        "ssh_host": "192.168.1.10",
        "ssh_user": "admin",
        "ssh_port": 22,
    }
    payload.update(overrides)
    resp = await client.post("/api/devices", json=payload)
    assert resp.status_code == 201
    return resp.json()


# ── GET /api/devices/{id}/metrics ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_device_metrics_not_found(client: AsyncClient):
    """GET /api/devices/99999/metrics returns 404 for unknown device."""
    resp = await client.get("/api/devices/99999/metrics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_device_metrics_no_data(client: AsyncClient):
    """GET /api/devices/{id}/metrics returns 404 when no snapshot exists."""
    dt_id = await _create_device_type(client)
    device = await _create_device(client, dt_id)
    resp = await client.get(f"/api/devices/{device['id']}/metrics")
    assert resp.status_code == 404
    assert "No metrics found" in resp.json()["detail"]


# ── GET /api/devices/{id}/metrics/history ─────────────────────────────────────


@pytest.mark.asyncio
async def test_get_device_metrics_history_not_found(client: AsyncClient):
    """GET /api/devices/99999/metrics/history returns 404 for unknown device."""
    resp = await client.get("/api/devices/99999/metrics/history")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_device_metrics_history_empty(client: AsyncClient):
    """GET /api/devices/{id}/metrics/history returns [] when no snapshots exist."""
    dt_id = await _create_device_type(client)
    device = await _create_device(client, dt_id)
    resp = await client.get(f"/api/devices/{device['id']}/metrics/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_device_metrics_history_hours_param(client: AsyncClient):
    """hours query param is accepted and passed through."""
    dt_id = await _create_device_type(client)
    device = await _create_device(client, dt_id)
    resp = await client.get(f"/api/devices/{device['id']}/metrics/history?hours=48")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_device_metrics_history_invalid_hours(client: AsyncClient):
    """hours < 1 or > 720 returns 422 validation error."""
    dt_id = await _create_device_type(client)
    device = await _create_device(client, dt_id)
    resp = await client.get(f"/api/devices/{device['id']}/metrics/history?hours=0")
    assert resp.status_code == 422
    resp2 = await client.get(f"/api/devices/{device['id']}/metrics/history?hours=1000")
    assert resp2.status_code == 422


# ── GET /api/devices/metrics/overview ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_metrics_overview_empty(client: AsyncClient):
    """GET /api/devices/metrics/overview returns empty list when no devices."""
    resp = await client.get("/api/devices/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["devices"] == []


@pytest.mark.asyncio
async def test_get_metrics_overview_active_devices(client: AsyncClient):
    """overview includes active devices, each with device_id, device_name, metrics."""
    dt_id = await _create_device_type(client)
    device1 = await _create_device(client, dt_id, name="Active-DUT", is_active=True)
    device2 = await _create_device(client, dt_id, name="Inactive-DUT", is_active=False)

    resp = await client.get("/api/devices/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()
    device_names = [d["device_name"] for d in data["devices"]]
    assert "Active-DUT" in device_names
    assert "Inactive-DUT" not in device_names


@pytest.mark.asyncio
async def test_metrics_overview_response_schema(client: AsyncClient):
    """overview response matches the expected schema structure."""
    dt_id = await _create_device_type(client)
    await _create_device(client, dt_id, name="Schema-DUT", is_active=True)

    resp = await client.get("/api/devices/metrics/overview")
    assert resp.status_code == 200
    data = resp.json()

    assert "devices" in data
    assert isinstance(data["devices"], list)
    item = data["devices"][0]
    assert "device_id" in item
    assert "device_name" in item
    assert "metrics" in item  # may be null when no snapshot exists
