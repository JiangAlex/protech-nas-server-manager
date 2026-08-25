"""Tests for firmware router (7 endpoints)."""

import pytest
from httpx import AsyncClient


async def _create_device_type(client: AsyncClient) -> int:
    resp = await client.post(
        "/api/device-types",
        json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"},
    )
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_list_firmware_empty(client: AsyncClient):
    """GET /api/firmware — empty list."""
    resp = await client.get("/api/firmware")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_firmware_filter_by_type(client: AsyncClient):
    """GET /api/firmware?device_type_id=X."""
    dt_id = await _create_device_type(client)
    # Create firmware
    await client.post(
        "/api/firmware",
        json={"device_type_id": dt_id, "version": "1.0.0"},
    )
    resp = await client.get(f"/api/firmware?device_type_id={dt_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_create_firmware(client: AsyncClient):
    """POST /api/firmware — create firmware version."""
    dt_id = await _create_device_type(client)
    payload = {
        "device_type_id": dt_id,
        "version": "1.0.0",
        "git_hash": "abc123",
        "git_hash_short": "abc",
        "changelog": "Initial release",
    }
    resp = await client.post("/api/firmware", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["version"] == "1.0.0"
    assert data["git_hash"] == "abc123"


@pytest.mark.asyncio
async def test_create_firmware_duplicate(client: AsyncClient):
    """POST /api/firmware — duplicate version returns 409."""
    dt_id = await _create_device_type(client)
    await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_firmware(client: AsyncClient):
    """GET /api/firmware/{id} — get created firmware."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    fw_id = create_resp.json()["id"]
    resp = await client.get(f"/api/firmware/{fw_id}")
    assert resp.status_code == 200
    assert resp.json()["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_get_firmware_not_found(client: AsyncClient):
    """GET /api/firmware/{id} — non-existent returns 404."""
    resp = await client.get("/api/firmware/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_firmware(client: AsyncClient):
    """PUT /api/firmware/{id} — update changelog."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0", "changelog": "Old"}
    )
    fw_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/firmware/{fw_id}", json={"changelog": "New changelog"}
    )
    assert resp.status_code == 200
    assert resp.json()["changelog"] == "New changelog"


@pytest.mark.asyncio
async def test_update_firmware_not_found(client: AsyncClient):
    """PUT /api/firmware/{id} — non-existent returns 404."""
    resp = await client.put("/api/firmware/9999", json={"changelog": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_firmware(client: AsyncClient):
    """DELETE /api/firmware/{id} — delete removes it."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    fw_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/firmware/{fw_id}")
    assert resp.status_code == 204
    resp2 = await client.get(f"/api/firmware/{fw_id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_firmware_not_found(client: AsyncClient):
    """DELETE /api/firmware/{id} — non-existent returns 404."""
    resp = await client.delete("/api/firmware/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_as_latest(client: AsyncClient):
    """POST /api/firmware/{id}/latest — marks latest."""
    dt_id = await _create_device_type(client)
    # Create two firmware versions
    fw1_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    fw2_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "2.0.0"}
    )
    fw2_id = fw2_resp.json()["id"]

    # Mark fw2 as latest
    resp = await client.post(f"/api/firmware/{fw2_id}/latest")
    assert resp.status_code == 200
    assert resp.json()["is_latest"] is True


@pytest.mark.asyncio
async def test_mark_as_latest_not_found(client: AsyncClient):
    """POST /api/firmware/{id}/latest — non-existent returns 404."""
    resp = await client.post("/api/firmware/9999/latest")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_mark_as_stable(client: AsyncClient):
    """POST /api/firmware/{id}/stable — marks stable."""
    dt_id = await _create_device_type(client)
    create_resp = await client.post(
        "/api/firmware", json={"device_type_id": dt_id, "version": "1.0.0"}
    )
    fw_id = create_resp.json()["id"]
    resp = await client.post(f"/api/firmware/{fw_id}/stable")
    assert resp.status_code == 200
    assert resp.json()["is_stable"] is True


@pytest.mark.asyncio
async def test_mark_as_stable_not_found(client: AsyncClient):
    """POST /api/firmware/{id}/stable — non-existent returns 404."""
    resp = await client.post("/api/firmware/9999/stable")
    assert resp.status_code == 404
