"""Tests for devices router (5 endpoints)."""

import pytest
from httpx import AsyncClient


async def _create_device_type(client: AsyncClient) -> int:
    """Helper: create a device type and return its ID."""
    resp = await client.post(
        "/api/device-types",
        json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_devices_empty(client: AsyncClient):
    """GET /api/devices — empty list."""
    resp = await client.get("/api/devices")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_devices_filter_by_type(client: AsyncClient):
    """GET /api/devices?device_type_id=X returns matching devices."""
    dt_id = await _create_device_type(client)
    # Create a device
    await client.post(
        "/api/devices",
        json={"device_type_id": dt_id, "name": "Device-1"},
    )
    resp = await client.get(f"/api/devices?device_type_id={dt_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Device-1"


@pytest.mark.asyncio
async def test_create_device(client: AsyncClient):
    """POST /api/devices — create a device."""
    dt_id = await _create_device_type(client)
    payload = {
        "device_type_id": dt_id,
        "name": "Device-1",
        "description": "Test device",
        "sku": "SKU001",
        "customer_id": "CUST-001",
    }
    resp = await client.post("/api/devices", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Device-1"
    assert data["sku"] == "SKU001"


@pytest.mark.asyncio
async def test_create_device_invalid_type(client: AsyncClient):
    """POST /api/devices — invalid device_type_id returns 400."""
    resp = await client.post(
        "/api/devices", json={"device_type_id": 9999, "name": "Bad"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_device_duplicate_name(client: AsyncClient):
    """POST /api/devices — duplicate name returns 409."""
    dt_id = await _create_device_type(client)
    await client.post("/api/devices", json={"device_type_id": dt_id, "name": "Dup"})
    resp = await client.post("/api/devices", json={"device_type_id": dt_id, "name": "Dup"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_device(client: AsyncClient):
    """GET /api/devices/{id} — get created device."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/devices", json={"device_type_id": dt_id, "name": "Device-1"}
    )
    dev_id = create_resp.json()["id"]
    resp = await client.get(f"/api/devices/{dev_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Device-1"


@pytest.mark.asyncio
async def test_get_device_not_found(client: AsyncClient):
    """GET /api/devices/{id} — non-existent returns 404."""
    resp = await client.get("/api/devices/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_device(client: AsyncClient):
    """PUT /api/devices/{id} — update name."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/devices", json={"device_type_id": dt_id, "name": "Device-1"}
    )
    dev_id = create_resp.json()["id"]
    resp = await client.put(f"/api/devices/{dev_id}", json={"name": "Device-Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Device-Updated"


@pytest.mark.asyncio
async def test_update_device_not_found(client: AsyncClient):
    """PUT /api/devices/{id} — non-existent returns 404."""
    resp = await client.put("/api/devices/9999", json={"name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_device(client: AsyncClient):
    """DELETE /api/devices/{id} — soft delete (sets is_active=False)."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/devices", json={"device_type_id": dt_id, "name": "Device-1"}
    )
    dev_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/devices/{dev_id}")
    assert resp.status_code == 204
    # Device still exists but is_active=False
    resp2 = await client.get(f"/api/devices/{dev_id}")
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is False
    # Device no longer appears in default (active) list
    resp3 = await client.get("/api/devices")
    active_ids = [d["id"] for d in resp3.json()]
    assert dev_id not in active_ids


@pytest.mark.asyncio
async def test_delete_device_not_found(client: AsyncClient):
    """DELETE /api/devices/{id} — non-existent returns 404."""
    resp = await client.delete("/api/devices/9999")
    assert resp.status_code == 404
