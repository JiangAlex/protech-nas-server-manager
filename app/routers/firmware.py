"""Firmware management API endpoints.

- GET    /api/firmware                - List firmware versions
- POST   /api/firmware               - Create firmware version
- GET    /api/firmware/{id}          - Get firmware details
- PUT    /api/firmware/{id}          - Update firmware version
- DELETE /api/firmware/{id}          - Delete firmware version
- POST   /api/firmware/{id}/latest   - Mark as latest
- POST   /api/firmware/{id}/stable   - Mark as stable
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.firmware import FirmwareCreate, FirmwareResponse, FirmwareUpdate
from app.services import firmware_service

router = APIRouter(prefix="/api/firmware", tags=["firmware"])


@router.get("", response_model=list[FirmwareResponse])
async def list_firmware(
    device_type_id: Optional[int] = Query(None, description="Filter by device type"),
    db: AsyncSession = Depends(get_db),
):
    """List all firmware versions."""
    return await firmware_service.get_firmware_list(db, device_type_id=device_type_id)


@router.post("", response_model=FirmwareResponse, status_code=status.HTTP_201_CREATED)
async def create_firmware(data: FirmwareCreate, db: AsyncSession = Depends(get_db)):
    """Create a new firmware version record."""
    # Check for duplicate version
    existing = await firmware_service.get_firmware_by_version(
        db, data.device_type_id, data.version
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Firmware version '{data.version}' already exists for this device type",
        )
    return await firmware_service.create_firmware(db, data)


@router.get("/{firmware_id}", response_model=FirmwareResponse)
async def get_firmware(firmware_id: int, db: AsyncSession = Depends(get_db)):
    """Get firmware version details."""
    firmware = await firmware_service.get_firmware(db, firmware_id)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")
    return firmware


@router.put("/{firmware_id}", response_model=FirmwareResponse)
async def update_firmware(
    firmware_id: int, data: FirmwareUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a firmware version."""
    firmware = await firmware_service.update_firmware(db, firmware_id, data)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")
    return firmware


@router.delete("/{firmware_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_firmware(firmware_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a firmware version."""
    deleted = await firmware_service.delete_firmware(db, firmware_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Firmware version not found")


@router.post("/{firmware_id}/latest", response_model=FirmwareResponse)
async def mark_as_latest(firmware_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a firmware version as the latest (unmarks previous latest of same type)."""
    firmware = await firmware_service.mark_as_latest(db, firmware_id)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")
    return firmware


@router.post("/{firmware_id}/stable", response_model=FirmwareResponse)
async def mark_as_stable(firmware_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a firmware version as stable."""
    firmware = await firmware_service.mark_as_stable(db, firmware_id)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")
    return firmware
