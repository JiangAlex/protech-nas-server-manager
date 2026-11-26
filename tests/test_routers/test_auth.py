"""Admin API authentication and device tokens (app/auth.py, app/services/device_auth_service.py)."""

import pytest
from httpx import AsyncClient

from app.config import get_settings


async def _setup(client: AsyncClient, mac: str | None = None):
    dt = (await client.post("/api/device-types", json={"name": "nas", "display_name": "NAS"})).json()
    fw = (await client.post("/api/firmware", json={"device_type_id": dt["id"], "version": "1.0.0"})).json()
    await client.post(f"/api/firmware/{fw['id']}/latest")
    await client.post(f"/api/firmware/{fw['id']}/stable")
    payload = {"device_type_id": dt["id"], "name": "NAS-1", "current_version": "0.9.0"}
    if mac:
        payload["mac_address"] = mac
    return (await client.post("/api/devices", json=payload)).json()


async def _events(client: AsyncClient, device_id: int) -> list[str]:
    resp = await client.get(f"/api/devices/{device_id}/auth-events")
    assert resp.status_code == 200
    return [e["event"] for e in resp.json()]


@pytest.fixture
def enforce():
    s = get_settings()
    old = s.device_token_enforce
    s.device_token_enforce = True
    yield
    s.device_token_enforce = old


# ── Admin API ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("get", "/api/devices"),
    ("post", "/api/devices"),
    ("get", "/api/device-types"),
    ("get", "/api/firmware"),
    ("post", "/api/firmware"),
    ("post", "/api/firmware/1/latest"),
    ("post", "/api/ota/batch/push"),
    ("get", "/api/ota/batch/status"),
    ("get", "/api/dashboard/metrics"),
    ("get", "/api/devices/1/metrics"),
    ("get", "/api/devices/1/auth-events"),
    ("post", "/api/devices/1/token/reset"),
    ("post", "/api/ota/nas/artifacts/1.0.0/upload"),
])
async def test_admin_api_needs_auth(anon_client: AsyncClient, method: str, path: str):
    resp = await getattr(anon_client, method)(path)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_api_wrong_key(anon_client: AsyncClient):
    resp = await anon_client.get("/api/devices", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_api_with_key(client: AsyncClient):
    assert (await client.get("/api/devices")).status_code == 200


@pytest.mark.asyncio
async def test_api_docs_off_by_default(anon_client: AsyncClient):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert (await anon_client.get(path)).status_code == 404


@pytest.mark.asyncio
async def test_health_stays_public(anon_client: AsyncClient):
    assert (await anon_client.get("/health")).status_code == 200


# ── Device tokens ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enroll_then_use_token(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client, mac="AA:BB:CC:00:11:22")
    body = {"device_id": dev["id"], "current_version": "0.9.0", "mac_address": "aa:bb:cc:00:11:22",
            "request_token": True}
    resp = await anon_client.post("/api/ota/nas/check", json=body)
    assert resp.status_code == 200
    token = resp.json()["device_token"]
    assert token and len(token) >= 40

    info = (await client.get(f"/api/devices/{dev['id']}")).json()
    assert info["has_device_token"] is True
    assert "token_hash" not in info

    # The token works; it is not sent again
    resp = await anon_client.post("/api/ota/nas/check", json=body, headers={"X-Device-Token": token})
    assert resp.status_code == 200
    assert resp.json()["device_token"] is None
    resp = await anon_client.get(f"/api/ota/nas/download/{dev['id']}", headers={"X-Device-Token": token})
    assert resp.status_code in (200, 404)

    events = await _events(client, dev["id"])
    assert "enrolled" in events
    assert "token_invalid" not in events


@pytest.mark.asyncio
async def test_wrong_token_rejected_and_logged(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client)
    body = {"device_id": dev["id"], "request_token": True}
    assert (await anon_client.post("/api/ota/nas/check", json=body)).json()["device_token"]

    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"]},
                                  headers={"X-Device-Token": "guess"})
    assert resp.status_code == 401
    resp = await anon_client.post("/api/ota/nas/report", headers={"X-Device-Token": "guess"},
                                  json={"device_id": dev["id"], "to_version": "1.0.0", "status": "completed"})
    assert resp.status_code == 401
    # The rejected attempts are kept although the request failed
    assert (await _events(client, dev["id"])).count("token_invalid") == 2


@pytest.mark.asyncio
async def test_no_second_enrollment(client: AsyncClient, anon_client: AsyncClient):
    """A stranger asking for a token for an enrolled device gets none."""
    dev = await _setup(client)
    body = {"device_id": dev["id"], "request_token": True}
    first = (await anon_client.post("/api/ota/nas/check", json=body)).json()["device_token"]
    second = await anon_client.post("/api/ota/nas/check", json=body)
    assert second.status_code == 200          # transition mode: allowed, but ...
    assert second.json()["device_token"] is None
    assert "enroll_rejected" in await _events(client, dev["id"])
    # ... the first token still works
    ok = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"]},
                                headers={"X-Device-Token": first})
    assert ok.status_code == 200


@pytest.mark.asyncio
async def test_enroll_refused_on_mac_mismatch(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client, mac="aa:bb:cc:00:11:22")
    resp = await anon_client.post("/api/ota/nas/check", json={
        "device_id": dev["id"], "mac_address": "de:ad:be:ef:00:01", "request_token": True})
    assert resp.status_code == 200
    assert resp.json()["device_token"] is None
    info = (await client.get(f"/api/devices/{dev['id']}")).json()
    assert info["has_device_token"] is False
    assert info["mac_address"] == "aa:bb:cc:00:11:22"   # not overwritten
    events = await _events(client, dev["id"])
    assert "enroll_rejected" in events and "mac_change_ignored" in events


@pytest.mark.asyncio
async def test_legacy_client_cannot_change_mac(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client, mac="aa:bb:cc:00:11:22")
    resp = await anon_client.post("/api/ota/nas/check", json={
        "device_id": dev["id"], "mac_address": "11:22:33:44:55:66"})
    assert resp.status_code == 200
    info = (await client.get(f"/api/devices/{dev['id']}")).json()
    assert info["mac_address"] == "aa:bb:cc:00:11:22"
    assert info["has_device_token"] is False
    events = await _events(client, dev["id"])
    assert "token_missing" in events and "mac_change_ignored" in events


@pytest.mark.asyncio
async def test_legacy_client_allowed_in_transition(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client)
    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"], "current_version": "0.9.0"})
    assert resp.status_code == 200
    assert resp.json()["update_available"] is True
    assert resp.json()["device_token"] is None


@pytest.mark.asyncio
async def test_enforce_rejects_missing_token(client: AsyncClient, anon_client: AsyncClient, enforce):
    dev = await _setup(client)
    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"]})
    assert resp.status_code == 401
    # Enrollment still works when enforcing (a new device asks for its token)
    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"], "request_token": True})
    assert resp.status_code == 200
    token = resp.json()["device_token"]
    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"]},
                                  headers={"X-Device-Token": token})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_reset_allows_new_enrollment(client: AsyncClient, anon_client: AsyncClient):
    dev = await _setup(client)
    body = {"device_id": dev["id"], "request_token": True}
    old = (await anon_client.post("/api/ota/nas/check", json=body)).json()["device_token"]

    resp = await client.post(f"/api/devices/{dev['id']}/token/reset")
    assert resp.status_code == 200
    assert resp.json()["has_device_token"] is False

    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": dev["id"]},
                                  headers={"X-Device-Token": old})
    assert resp.status_code == 401                       # the old token is gone
    new = (await anon_client.post("/api/ota/nas/check", json=body)).json()["device_token"]
    assert new and new != old
    events = await _events(client, dev["id"])
    assert events.count("enrolled") == 2 and "token_reset" in events


@pytest.mark.asyncio
async def test_unknown_device_logged(client: AsyncClient, anon_client: AsyncClient, db_session):
    from sqlalchemy import select
    from app.models.device_auth_event import DeviceAuthEvent

    resp = await anon_client.post("/api/ota/nas/check", json={"device_id": 4242, "request_token": True})
    assert resp.status_code == 200
    assert resp.json()["device_token"] is None
    rows = (await db_session.execute(select(DeviceAuthEvent))).scalars().all()
    assert [r.event for r in rows] == ["unknown_device"]
    assert rows[0].detail == "device_id 4242"
