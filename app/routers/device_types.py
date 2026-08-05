"""Device type management API endpoints.

- GET    /api/device-types      - List all device types
- POST   /api/device-types      - Create new device type
- PUT    /api/device-types/{id} - Update device type
- DELETE /api/device-types/{id} - Remove device type
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DeviceTypeCreate, DeviceTypeResponse, DeviceTypeUpdate
from app.services import device_service

router = APIRouter(prefix="/api/device-types", tags=["device-types"])


@router.get("", response_model=list[DeviceTypeResponse])
async def list_device_types(db: AsyncSession = Depends(get_db)):
    """List all device types."""
    return await device_service.get_device_types(db)


@router.post("", response_model=DeviceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_device_type(
    data: DeviceTypeCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new device type."""
    existing = await device_service.get_device_type_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device type '{data.name}' already exists",
        )
    return await device_service.create_device_type(db, data)


@router.get("/{device_type_id}", response_model=DeviceTypeResponse)
async def get_device_type(device_type_id: int, db: AsyncSession = Depends(get_db)):
    """Get a device type by ID."""
    device_type = await device_service.get_device_type(db, device_type_id)
    if not device_type:
        raise HTTPException(status_code=404, detail="Device type not found")
    return device_type


@router.put("/{device_type_id}", response_model=DeviceTypeResponse)
async def update_device_type(
    device_type_id: int, data: DeviceTypeUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a device type."""
    device_type = await device_service.update_device_type(db, device_type_id, data)
    if not device_type:
        raise HTTPException(status_code=404, detail="Device type not found")
    return device_type


@router.delete("/{device_type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device_type(device_type_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a device type."""
    deleted = await device_service.delete_device_type(db, device_type_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device type not found")
