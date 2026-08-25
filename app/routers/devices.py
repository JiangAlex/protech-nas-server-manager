"""Device CRUD API endpoints.

- GET    /api/devices                    - List devices (filter by type/status)
- POST   /api/devices                    - Register new device
- GET    /api/devices/{id}               - Get device details
- PUT    /api/devices/{id}               - Update device config
- DELETE /api/devices/{id}               - Remove device (soft delete)
- POST   /api/devices/{id}/health-check  - On-demand health check
"""

import asyncio
import socket
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DeviceCreate, DeviceListResponse, DeviceResponse, DeviceUpdate
from app.services import device_service


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
