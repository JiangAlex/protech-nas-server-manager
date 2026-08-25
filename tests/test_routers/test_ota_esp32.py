"""Tests for ota_esp32 router (3 endpoints)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_esp32_check_no_update(client: AsyncClient):
    """GET /api/ota/esp32/check — placeholder always returns no update."""
    resp = await client.get(
        "/api/ota/esp32/check",
        params={"mac": "AA:BB:CC:DD:EE:FF", "version": "1.0.0"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["update_available"] is False
    assert data["current_version"] == "1.0.0"


@pytest.mark.asyncio
async def test_esp32_check_missing_params(client: AsyncClient):
    """GET /api/ota/esp32/check — missing required params returns 422."""
    resp = await client.get("/api/ota/esp32/check")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_esp32_download_not_implemented(client: AsyncClient):
    """GET /api/ota/esp32/firmware/{version} — returns 501."""
    resp = await client.get("/api/ota/esp32/firmware/1.0.0")
    assert resp.status_code == 501


@pytest.mark.asyncio
async def test_esp32_report_success(client: AsyncClient):
    """POST /api/ota/esp32/report — successful update report."""
    resp = await client.post(
        "/api/ota/esp32/report",
        json={
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "from_version": "1.0.0",
            "to_version": "1.1.0",
            "status": "completed",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "AA:BB:CC:DD:EE:FF" in data["message"]


@pytest.mark.asyncio
async def test_esp32_report_failure(client: AsyncClient):
    """POST /api/ota/esp32/report — failed update report."""
    resp = await client.post(
        "/api/ota/esp32/report",
        json={
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "from_version": "1.0.0",
            "to_version": "1.1.0",
            "status": "failed",
            "error_message": "Flash failed",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
