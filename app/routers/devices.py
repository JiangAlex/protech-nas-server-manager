"""Device CRUD API endpoints.

- GET    /api/devices                    - List devices (filter by type/status)
- POST   /api/devices                    - Register new device
- GET    /api/devices/{id}               - Get device details
- PUT    /api/devices/{id}               - Update device config
- DELETE /api/devices/{id}               - Remove device (soft delete)
- POST   /api/devices/{id}/health-check  - On-demand health check
- GET    /api/devices/{id}/auth-events   - Device token audit log (newest first)
- POST   /api/devices/{id}/token/reset   - Forget the device token; the device enrolls again on its next check
"""

import asyncio
import socket
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth import require_admin
from app.models.device import Device
from app.schemas import DeviceAuthEventResponse, DeviceCreate, DeviceListResponse, DeviceResponse, DeviceUpdate
from app.services import device_auth_service, device_service


class HealthCheckResponse(BaseModel):
    device_id: int
    status: str  # "online" | "offline"
    method: str
    latency_ms: float
    message: str

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=list[DeviceListResponse])
async def list_devices(
    device_type_id: Optional[int] = Query(None, description="Filter by device type"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
):
    """List all devices with optional filters."""
    return await device_service.get_devices(
        db, device_type_id=device_type_id, status=status_filter, is_active=is_active
    )


@router.post("", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_device(data: DeviceCreate, db: AsyncSession = Depends(get_db)):
    """Register a new device."""
    # Check device type exists
    device_type = await device_service.get_device_type(db, data.device_type_id)
    if not device_type:
        raise HTTPException(status_code=400, detail="Invalid device_type_id")
    # Check name unique
    existing = await device_service.get_device_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{data.name}' already exists",
        )
    return await device_service.create_device(db, data)


@router.get("/{device_id}", response_model=DeviceResponse)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)):
    """Get device details."""
    device = await device_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.put("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int, data: DeviceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update device configuration."""
    device = await device_service.update_device(db, device_id, data)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await db.commit()
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete a device (deactivate)."""
    deleted = await device_service.delete_device(db, device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_id}/health-check", response_model=HealthCheckResponse)
async def health_check_device(device_id: int, db: AsyncSession = Depends(get_db)):
    """Perform on-demand health check on a device.
    
    Uses TCP connect to ssh_host (or ip_address) as a ping.
    Returns latency in ms.
    """
    device = await device_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    target = device.ssh_host or device.ip_address
    port = device.ssh_port or 22
    timeout = 5.0

    if not target:
        return HealthCheckResponse(
            device_id=device_id,
            status="offline",
            method="tcp",
            latency_ms=0.0,
            message="No ssh_host or ip_address configured",
        )

    try:
        start = asyncio.get_event_loop().time()
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(target, port),
            timeout=timeout,
        )
        writer.close()
        await writer.wait_closed()
        latency = (asyncio.get_event_loop().time() - start) * 1000
        return HealthCheckResponse(
            device_id=device_id,
            status="online",
            method="tcp_connect",
            latency_ms=round(latency, 2),
            message=f"Connected to {target}:{port}",
        )
    except asyncio.TimeoutError:
        return HealthCheckResponse(
            device_id=device_id,
            status="offline",
            method="tcp_connect",
            latency_ms=timeout * 1000,
            message=f"Connection timed out ({target}:{port})",
        )
    except (OSError, socket.gaierror) as e:
        return HealthCheckResponse(
            device_id=device_id,
            status="offline",
            method="tcp_connect",
            latency_ms=0.0,
            message=f"Connection failed: {e}",
        )


@router.get("/{device_id}/auth-events", response_model=list[DeviceAuthEventResponse])
async def list_auth_events(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Device token audit log: enrollments, wrong or missing tokens, refused enrollments, resets."""
    if not await db.get(Device, device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    return await device_auth_service.list_events(db, device_id, limit)


@router.post("/{device_id}/token/reset", response_model=DeviceResponse)
async def reset_device_token(
    device_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(require_admin),
):
    """Forget the device token. The device gets a new one on its next check with request_token.

    Use it when a device was replaced or reinstalled, or when the token may have leaked.
    """
    device = await db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    await device_auth_service.reset_token(db, request, device, admin)
    await db.flush()
    await db.refresh(device)
    return device
