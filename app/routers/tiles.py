"""Map tile endpoints for the ESP32 boards (device side). Rules in app/services/tile_proxy_service.py.

- POST /api/tiles/plan?mac=              - tiles a GPX route needs (body = GPX)
- GET  /api/tiles/{z}/{x}/{y}.bin?mac=   - one tile (&fmt=tz1: compressed)

Authentication: X-Device-Token, always required.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import tile_proxy_service

router = APIRouter(prefix="/api/tiles", tags=["tiles"])


@router.post("/plan")
async def tile_plan(
    request: Request,
    mac: str = Query(..., description="ESP32 MAC address"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """The tiles (one "z x y" line each) that a GPX route needs."""
    await tile_proxy_service.authorize(db, request, mac, "tiles_plan")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > tile_proxy_service.MAX_GPX_BYTES:
        raise HTTPException(status_code=413, detail="GPX file too large (at most 4 MB)")
    return await tile_proxy_service.plan(await request.body())


@router.get("/{z}/{x}/{y}.bin")
async def get_tile(
    request: Request,
    z: int = Path(ge=12, le=18),
    x: int = Path(ge=0, le=9_999_999),
    y: int = Path(ge=0, le=9_999_999),
    mac: str = Query(..., description="ESP32 MAC address"),
    fmt: Optional[str] = Query(None, description="tz1 = compressed"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """One map tile."""
    await tile_proxy_service.authorize(db, request, mac, "tiles_get")
    return await tile_proxy_service.tile(z, x, y, fmt)
