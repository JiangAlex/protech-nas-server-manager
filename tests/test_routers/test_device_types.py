"""Tests for device-types router (5 endpoints)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_device_types_empty(client: AsyncClient):
    """GET /api/device-types — empty list."""
    resp = await client.get("/api/device-types")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_device_type(client: AsyncClient):
    """POST /api/device-types — create a device type."""
    payload = {"name": "NAS-Pro", "display_name": "ProTech NAS Pro"}
    resp = await client.post("/api/device-types", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "NAS-Pro"
    assert data["display_name"] == "ProTech NAS Pro"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_create_device_type_duplicate(client: AsyncClient):
    """POST /api/device-types — duplicate name returns 409."""
    payload = {"name": "NAS-Pro", "display_name": "ProTech NAS Pro"}
    await client.post("/api/device-types", json=payload)
    resp = await client.post("/api/device-types", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_device_type(client: AsyncClient):
    """GET /api/device-types/{id} — get created device type."""
    create_resp = await client.post(
        "/api/device-types", json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"}
    )
    dt_id = create_resp.json()["id"]
    resp = await client.get(f"/api/device-types/{dt_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "NAS-Pro"


@pytest.mark.asyncio
async def test_get_device_type_not_found(client: AsyncClient):
    """GET /api/device-types/{id} — non-existent returns 404."""
    resp = await client.get("/api/device-types/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_device_type(client: AsyncClient):
    """PUT /api/device-types/{id} — update display name."""
    create_resp = await client.post(
        "/api/device-types", json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"}
    )
    dt_id = create_resp.json()["id"]
    resp = await client.put(
        f"/api/device-types/{dt_id}", json={"display_name": "Updated Name"}
    )
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_device_type_not_found(client: AsyncClient):
    """PUT /api/device-types/{id} — non-existent returns 404."""
    resp = await client.put("/api/device-types/9999", json={"display_name": "X"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_type(client: AsyncClient):
    """DELETE /api/device-types/{id} — delete removes it from list."""
    create_resp = await client.post(
        "/api/device-types", json={"name": "NAS-Pro", "display_name": "ProTech NAS Pro"}
    )
    dt_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/device-types/{dt_id}")
    assert resp.status_code == 204
    # Verify it's gone
    resp2 = await client.get(f"/api/device-types/{dt_id}")
    assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_device_type_not_found(client: AsyncClient):
    """DELETE /api/device-types/{id} — non-existent returns 404."""
    resp = await client.delete("/api/device-types/9999")
    assert resp.status_code == 404
