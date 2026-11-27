"""Map tiles for the ESP32 boards: /api/tiles (tile_proxy_service). The tile server is a mock transport."""

import httpx
import pytest
from httpx import AsyncClient

from app.config import get_settings
from app.services import tile_proxy_service

MAC = "aa:bb:cc:dd:ee:02"
UPSTREAM = "http://tiles.test:8090"
calls: list[httpx.Request] = []


def upstream(request: httpx.Request) -> httpx.Response:
    calls.append(request)
    path = request.url.path
    if request.method == "POST" and path == "/plan":
        return httpx.Response(200, content=b"12 3425 1752\n13 6850 3504\n", headers={"content-type": "text/plain"})
    if path == "/tile/16/54800/28060.bin":
        kind = "tz1" if request.url.query == b"fmt=tz1" else "tile"
        return httpx.Response(200, content=b"TZ1\0data" if kind == "tz1" else b"\1" * 8,
                              headers={"content-type": "application/octet-stream", "x-tile-kind": kind})
    if path == "/tile/16/1/1.bin":
        return httpx.Response(404, content=b"outside Taiwan or zoom 12-18\n")
    if path == "/tile/16/2/2.bin":
        return httpx.Response(503, content=b"render failed, try again later\n")
    if path == "/tile/16/3/3.bin":
        raise httpx.ConnectError("down")
    return httpx.Response(404)


@pytest.fixture(autouse=True)
def tile_upstream(monkeypatch):
    calls.clear()
    monkeypatch.setattr(get_settings(), "tile_upstream_url", UPSTREAM)
    monkeypatch.setattr(tile_proxy_service, "_client", httpx.AsyncClient(transport=httpx.MockTransport(upstream)))
    monkeypatch.setattr(tile_proxy_service, "_sem", None)


async def _enrolled(client: AsyncClient, anon: AsyncClient) -> str:
    dt = (await client.post("/api/device-types", json={"name": "lcd2", "display_name": "LCD2",
                                                        "update_method": "ota_http"})).json()
    await client.post("/api/devices", json={"device_type_id": dt["id"], "name": "LCD2-1", "mac_address": MAC})
    r = await anon.get("/api/ota/esp32/check", params={"mac": MAC, "version": "1.0.0", "request_token": "true"})
    return r.json()["device_token"]


@pytest.mark.asyncio
async def test_tile_and_plan_with_token(client: AsyncClient, anon_client: AsyncClient):
    token = await _enrolled(client, anon_client)
    h = {"X-Device-Token": token}
    r = await anon_client.get("/api/tiles/16/54800/28060.bin", params={"mac": MAC}, headers=h)
    assert r.status_code == 200 and r.content == b"\1" * 8 and r.headers["x-tile-kind"] == "tile"
    r = await anon_client.get("/api/tiles/16/54800/28060.bin", params={"mac": MAC, "fmt": "tz1"}, headers=h)
    assert r.status_code == 200 and r.content.startswith(b"TZ1") and r.headers["x-tile-kind"] == "tz1"
    r = await anon_client.post("/api/tiles/plan", params={"mac": MAC}, headers=h, content=b"<gpx/>")
    assert r.status_code == 200 and r.text.startswith("12 3425 1752")
    post = [c for c in calls if c.method == "POST"][0]
    assert post.content == b"<gpx/>" and post.headers["content-type"] == "application/gpx+xml"
    # the token is not passed on to the tile server
    assert all("x-device-token" not in c.headers for c in calls)


@pytest.mark.asyncio
async def test_token_required(client: AsyncClient, anon_client: AsyncClient):
    token = await _enrolled(client, anon_client)
    url = "/api/tiles/16/54800/28060.bin"
    assert (await anon_client.get(url, params={"mac": MAC})).status_code == 401
    assert (await anon_client.get(url, params={"mac": MAC}, headers={"X-Device-Token": "wrong"})).status_code == 401
    assert (await anon_client.post("/api/tiles/plan", params={"mac": MAC}, content=b"x")).status_code == 401
    assert (await anon_client.get(url, params={"mac": "11:22:33:44:55:66"},
                                  headers={"X-Device-Token": token})).status_code == 404
    assert calls == []   # nothing reached the tile server


@pytest.mark.asyncio
async def test_upstream_answers(client: AsyncClient, anon_client: AsyncClient):
    h = {"X-Device-Token": await _enrolled(client, anon_client)}
    get = lambda path: anon_client.get(path, params={"mac": MAC}, headers=h)
    assert (await get("/api/tiles/16/1/1.bin")).status_code == 404       # outside the map
    assert (await get("/api/tiles/16/2/2.bin")).status_code == 503       # render failed, retry
    assert (await get("/api/tiles/16/3/3.bin")).status_code == 502       # tile server down
    assert (await get("/api/tiles/11/1/1.bin")).status_code == 422       # zoom outside 12-18


@pytest.mark.asyncio
async def test_not_configured(client: AsyncClient, anon_client: AsyncClient, monkeypatch):
    h = {"X-Device-Token": await _enrolled(client, anon_client)}
    monkeypatch.setattr(get_settings(), "tile_upstream_url", "")
    r = await anon_client.get("/api/tiles/16/54800/28060.bin", params={"mac": MAC}, headers=h)
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_plan_limits(client: AsyncClient, anon_client: AsyncClient):
    h = {"X-Device-Token": await _enrolled(client, anon_client)}
    r = await anon_client.post("/api/tiles/plan", params={"mac": MAC}, headers=h, content=b"")
    assert r.status_code == 411
    r = await anon_client.post("/api/tiles/plan", params={"mac": MAC}, headers=h,
                               content=b"x" * (tile_proxy_service.MAX_GPX_BYTES + 1))
    assert r.status_code == 413
