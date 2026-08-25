"""Tests for ota_batch router (2 endpoints)."""

import pytest
from httpx import AsyncClient


async def _create_device_type_and_firmware(client: AsyncClient):
    """Helper: create a device type + firmware and return their IDs."""
    dt_resp = await client.post(
        "/api/device-types",
        json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"},
    )
    dt_id = dt_resp.json()["id"]
    fw_resp = await client.post(
        "/api/firmware",
        json={"device_type_id": dt_id, "version": "1.0.0"},
    )
    fw_id = fw_resp.json()["id"]
    return dt_id, fw_id


async def _create_device(client: AsyncClient, dt_id: int, name: str = "Device-1", **kwargs):
    """Helper: create a device."""
    payload = {"device_type_id": dt_id, "name": name, **kwargs}
    resp = await client.post("/api/devices", json=payload)
    return resp.json()


@pytest.mark.asyncio
async def test_batch_push_no_target(client: AsyncClient):
    """POST /api/ota/batch/push — no target filter returns 400."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_batch_push_firmware_not_found(client: AsyncClient):
    """POST /api/ota/batch/push — invalid firmware returns 404."""
    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": 9999, "all_devices": True},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_batch_push_by_device_ids(client: AsyncClient):
    """POST /api/ota/batch/push — targets specific device IDs."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    dev = await _create_device(client, dt_id, "Device-1")

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "device_ids": [dev["id"]]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["total_devices"] == 1
    assert data["targeted_devices"][0]["name"] == "Device-1"


@pytest.mark.asyncio
async def test_batch_push_by_sku(client: AsyncClient):
    """POST /api/ota/batch/push — targets devices by SKU."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1", sku="SKU001")
    await _create_device(client, dt_id, "Device-2", sku="SKU001")

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "sku": "SKU001"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_devices"] == 2


@pytest.mark.asyncio
async def test_batch_push_by_customer_id(client: AsyncClient):
    """POST /api/ota/batch/push — targets devices by customer_id."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1", customer_id="CUST-A")
    await _create_device(client, dt_id, "Device-2", customer_id="CUST-A")

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "customer_id": "CUST-A"},
    )
    assert resp.status_code == 200
    assert resp.json()["total_devices"] == 2


@pytest.mark.asyncio
async def test_batch_push_by_device_type_id(client: AsyncClient):
    """POST /api/ota/batch/push — targets all devices of a type."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1")
    await _create_device(client, dt_id, "Device-2")

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "device_type_id": dt_id},
    )
    assert resp.status_code == 200
    assert resp.json()["total_devices"] == 2


@pytest.mark.asyncio
async def test_batch_push_all_devices(client: AsyncClient):
    """POST /api/ota/batch/push — all active devices."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1")
    await _create_device(client, dt_id, "Device-2")

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "all_devices": True},
    )
    assert resp.status_code == 200
    assert resp.json()["total_devices"] == 2


@pytest.mark.asyncio
async def test_batch_push_no_matching_devices(client: AsyncClient):
    """POST /api/ota/batch/push — no matching devices returns success=False."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)

    resp = await client.post(
        "/api/ota/batch/push",
        json={"firmware_id": fw_id, "device_ids": [9999]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["total_devices"] == 0


@pytest.mark.asyncio
async def test_batch_status_empty(client: AsyncClient):
    """GET /api/ota/batch/status — no devices returns empty list."""
    resp = await client.get("/api/ota/batch/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["devices"] == []


@pytest.mark.asyncio
async def test_batch_status_by_sku(client: AsyncClient):
    """GET /api/ota/batch/status?sku=X returns device statuses."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1", sku="SKU001")
    await _create_device(client, dt_id, "Device-2", sku="SKU001")

    resp = await client.get("/api/ota/batch/status?sku=SKU001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_batch_status_by_customer_id(client: AsyncClient):
    """GET /api/ota/batch/status?customer_id=X."""
    dt_id, fw_id = await _create_device_type_and_firmware(client)
    await _create_device(client, dt_id, "Device-1", customer_id="CUST-A")

    resp = await client.get("/api/ota/batch/status?customer_id=CUST-A")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
