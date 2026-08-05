"""Device management service layer.

Handles CRUD operations for devices and device types.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.device import Device, DeviceType
from app.schemas import DeviceCreate, DeviceTypeCreate, DeviceTypeUpdate, DeviceUpdate


# ── DeviceType CRUD ─────────────────────────────────────────


async def get_device_types(db: AsyncSession) -> list[DeviceType]:
    """Get all device types."""
    result = await db.execute(select(DeviceType).order_by(DeviceType.id))
    return list(result.scalars().all())


async def get_device_type(db: AsyncSession, device_type_id: int) -> Optional[DeviceType]:
    """Get a device type by ID."""
    result = await db.execute(select(DeviceType).where(DeviceType.id == device_type_id))
    return result.scalar_one_or_none()


async def get_device_type_by_name(db: AsyncSession, name: str) -> Optional[DeviceType]:
    """Get a device type by name."""
    result = await db.execute(select(DeviceType).where(DeviceType.name == name))
    return result.scalar_one_or_none()


async def create_device_type(db: AsyncSession, data: DeviceTypeCreate) -> DeviceType:
    """Create a new device type."""
    device_type = DeviceType(**data.model_dump())
    db.add(device_type)
    await db.flush()
    await db.refresh(device_type)
    return device_type


async def update_device_type(
    db: AsyncSession, device_type_id: int, data: DeviceTypeUpdate
) -> Optional[DeviceType]:
    """Update a device type."""
    device_type = await get_device_type(db, device_type_id)
    if not device_type:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(device_type, key, value)
    await db.flush()
    await db.refresh(device_type)
    return device_type


async def delete_device_type(db: AsyncSession, device_type_id: int) -> bool:
    """Delete a device type."""
    device_type = await get_device_type(db, device_type_id)
    if not device_type:
        return False
    await db.delete(device_type)
    await db.flush()
    return True


# ── Device CRUD ─────────────────────────────────────────────


async def get_devices(
    db: AsyncSession,
    device_type_id: Optional[int] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> list[Device]:
    """Get all devices with optional filters."""
    query = select(Device).order_by(Device.id)
    if device_type_id is not None:
        query = query.where(Device.device_type_id == device_type_id)
    if status is not None:
        query = query.where(Device.status == status)
    if is_active is not None:
        query = query.where(Device.is_active == is_active)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_device(db: AsyncSession, device_id: int) -> Optional[Device]:
    """Get a device by ID with device type loaded."""
    result = await db.execute(
        select(Device)
        .options(selectinload(Device.device_type))
        .where(Device.id == device_id)
    )
    return result.scalar_one_or_none()


async def get_device_by_name(db: AsyncSession, name: str) -> Optional[Device]:
    """Get a device by name."""
    result = await db.execute(select(Device).where(Device.name == name))
    return result.scalar_one_or_none()


async def create_device(db: AsyncSession, data: DeviceCreate) -> Device:
    """Create a new device."""
    device = Device(**data.model_dump())
    db.add(device)
    await db.flush()
    await db.refresh(device)
    return device


async def update_device(
    db: AsyncSession, device_id: int, data: DeviceUpdate
) -> Optional[Device]:
    """Update a device."""
    device = await get_device(db, device_id)
    if not device:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(device, key, value)
    await db.flush()
    await db.refresh(device)
    return device


async def delete_device(db: AsyncSession, device_id: int) -> bool:
    """Soft delete a device (set is_active=False)."""
    device = await get_device(db, device_id)
    if not device:
        return False
    device.is_active = False
    await db.flush()
    return True


async def get_device_count_by_status(db: AsyncSession) -> dict[str, int]:
    """Get device count grouped by status."""
    devices = await get_devices(db)
    counts: dict[str, int] = {"total": 0, "online": 0, "offline": 0, "unknown": 0}
    for device in devices:
        counts["total"] += 1
        if device.status in counts:
            counts[device.status] += 1
        else:
            counts[device.status] = 1
    return counts
