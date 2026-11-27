"""Map tiles for the ESP32 boards, fetched from the tile server on behalf of the board.

The tile server (~/osm-tiles/tile_server.py on the tile PC) answers private networks only. A board on a
phone hotspot cannot reach it, so it asks this server instead; the request is passed on, and the answer
comes back unchanged:

- POST /api/tiles/plan?mac=            body = a GPX file     -> "z x y" lines, one per tile the route needs
- GET  /api/tiles/{z}/{x}/{y}.bin?mac=[&fmt=tz1]             -> the tile (131072 bytes, 2 bytes plain color,
                                                                or compressed "TZ1" with fmt=tz1)

Authentication is the device token of the board (X-Device-Token), always required, like the ESP32 OTA.
Without TILE_UPSTREAM_URL the service answers 503.
"""

import asyncio
from typing import Optional

import httpx
import structlog
from fastapi import HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services import device_auth_service, ota_esp32_service

logger = structlog.get_logger()

MAX_GPX_BYTES = 4 * 1024 * 1024   # same limit as the tile server

_client: Optional[httpx.AsyncClient] = None
_sem: Optional[tuple[asyncio.AbstractEventLoop, asyncio.Semaphore]] = None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        s = get_settings()
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(s.tile_upstream_timeout_seconds, connect=5.0),
            limits=httpx.Limits(max_connections=s.tile_max_concurrent, max_keepalive_connections=s.tile_max_concurrent),
        )
    return _client


def _slots() -> asyncio.Semaphore:
    """Limits the requests to the tile PC (rendering a tile is heavy there)."""
    global _sem
    loop = asyncio.get_running_loop()
    if _sem is None or _sem[0] is not loop:
        _sem = (loop, asyncio.Semaphore(max(1, get_settings().tile_max_concurrent)))
    return _sem[1]


async def authorize(db: AsyncSession, request: Request, mac: str, endpoint: str) -> None:
    """The board must be a registered, active device with a valid token. Raises 404 / 401."""
    device = await ota_esp32_service.find_device(db, mac)
    if device is None:
        await device_auth_service.log_event(db, request, None, "unknown_device", endpoint, mac, f"mac {mac}")
        await db.commit()   # get_db() would roll the audit row back when the request raises
        raise HTTPException(status_code=404, detail="Unknown device")
    await device_auth_service.authenticate(db, request, device, endpoint, mac=mac, enforce=True)
    # The tile server can take seconds: do not hold the database transaction meanwhile
    await db.commit()


async def _forward(method: str, path: str, **kw) -> Response:
    base = get_settings().tile_upstream_url.rstrip("/")
    if not base:
        raise HTTPException(status_code=503, detail="Tile service is not configured")
    try:
        async with _slots():
            r = await _http().request(method, base + path, **kw)
    except httpx.HTTPError as e:
        logger.warning("tile_upstream_unreachable", path=path, error=type(e).__name__)
        raise HTTPException(status_code=502, detail="Tile server does not answer")
    if r.status_code == 200:
        headers = {"X-Tile-Kind": r.headers["x-tile-kind"]} if "x-tile-kind" in r.headers else {}
        return Response(content=r.content, media_type=r.headers.get("content-type", "application/octet-stream"),
                        headers=headers)
    if r.status_code in (404, 411, 413, 422):   # the board's request was wrong or outside the map: say so
        raise HTTPException(status_code=r.status_code, detail=r.text.strip()[:200] or "Tile server refused")
    # 503 (render failed), 403 (this server is not allowed there) and anything else
    logger.warning("tile_upstream_error", path=path, status=r.status_code)
    raise HTTPException(status_code=503 if r.status_code == 503 else 502, detail="Tile server error")


async def plan(gpx: bytes) -> Response:
    if not gpx:
        raise HTTPException(status_code=411, detail="Send a GPX file")
    if len(gpx) > MAX_GPX_BYTES:
        raise HTTPException(status_code=413, detail="GPX file too large (at most 4 MB)")
    resp = await _forward("POST", "/plan", content=gpx, headers={"Content-Type": "application/gpx+xml"})
    logger.info("tile_plan", gpx_bytes=len(gpx), lines=resp.body.count(b"\n"))
    return resp


async def tile(z: int, x: int, y: int, fmt: Optional[str]) -> Response:
    query = "?fmt=tz1" if fmt == "tz1" else ""
    return await _forward("GET", f"/tile/{z}/{x}/{y}.bin{query}")
