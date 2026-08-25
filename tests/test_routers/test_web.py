"""Tests for web/admin router (10 endpoints).

Note: These are HTML response tests for server-side rendered pages.
Auth is handled via session cookie — get_current_user raises HTTPException 303
which httpx follows by default in follow_redirects=True mode.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_web_login_page(client: AsyncClient):
    """GET /admin/login — shows login form."""
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    assert "login" in resp.text.lower()


@pytest.mark.asyncio
async def test_web_login_success(client: AsyncClient):
    """POST /admin/login — valid credentials redirect to dashboard."""
    resp = await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_login_failure(client: AsyncClient):
    """POST /admin/login — wrong credentials shows error."""
    resp = await client.post(
        "/admin/login",
        data={"username": "admin", "password": "wrong"},
        follow_redirects=False,
    )
    assert resp.status_code == 200  # re-renders login with error
    assert "錯誤" in resp.text or "error" in resp.text.lower()


@pytest.mark.asyncio
async def test_web_logout(client: AsyncClient):
    """GET /admin/logout — clears session and redirects to login."""
    resp = await client.get("/admin/logout", follow_redirects=True)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_dashboard_unauthenticated(client: AsyncClient):
    """GET /admin/ — unauthenticated redirects to login (303)."""
    resp = await client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 303


@pytest.mark.asyncio
async def test_web_dashboard_authenticated(client: AsyncClient):
    """GET /admin/ — authenticated returns dashboard HTML."""
    # Login first
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 200
    assert "device" in resp.text.lower()


@pytest.mark.asyncio
async def test_web_devices_list_unauthenticated(client: AsyncClient):
    """GET /admin/devices/ — unauthenticated redirects."""
    resp = await client.get("/admin/devices/", follow_redirects=False)
    assert resp.status_code == 303


@pytest.mark.asyncio
async def test_web_devices_list_authenticated(client: AsyncClient):
    """GET /admin/devices/ — authenticated returns device list."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/devices/", follow_redirects=False)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_device_detail_not_found(client: AsyncClient):
    """GET /admin/devices/{id}/ — non-existent device returns 404."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/devices/9999/", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_web_device_types_page_unauthenticated(client: AsyncClient):
    """GET /admin/device-types/ — unauthenticated redirects."""
    resp = await client.get("/admin/device-types/", follow_redirects=False)
    assert resp.status_code == 303


@pytest.mark.asyncio
async def test_web_device_types_page_authenticated(client: AsyncClient):
    """GET /admin/device-types/ — authenticated returns page."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/device-types/", follow_redirects=False)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_firmware_page_unauthenticated(client: AsyncClient):
    """GET /admin/firmware/ — unauthenticated redirects."""
    resp = await client.get("/admin/firmware/", follow_redirects=False)
    assert resp.status_code == 303


@pytest.mark.asyncio
async def test_web_firmware_page_authenticated(client: AsyncClient):
    """GET /admin/firmware/ — authenticated returns page."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/firmware/", follow_redirects=False)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_updates_page_authenticated(client: AsyncClient):
    """GET /admin/updates/ — authenticated returns page."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/updates/", follow_redirects=False)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_web_batch_update_page_authenticated(client: AsyncClient):
    """GET /admin/batch-update/ — authenticated returns page."""
    await client.post(
        "/admin/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    resp = await client.get("/admin/batch-update/", follow_redirects=False)
    assert resp.status_code == 200
