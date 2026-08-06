"""Firmware version management service.

Handles CRUD operations, marking latest/stable, and version display generation.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.firmware import FirmwareVersion
from app.schemas.firmware import FirmwareCreate, FirmwareUpdate


async def get_firmware_list(
    db: AsyncSession,
    device_type_id: Optional[int] = None,
) -> list[FirmwareVersion]:
    """Get all firmware versions with optional filter."""
    query = select(FirmwareVersion).order_by(FirmwareVersion.id.desc())
    if device_type_id is not None:
        query = query.where(FirmwareVersion.device_type_id == device_type_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_firmware(db: AsyncSession, firmware_id: int) -> Optional[FirmwareVersion]:
    """Get a firmware version by ID."""
    return await db.get(FirmwareVersion, firmware_id)


async def get_firmware_by_version(
    db: AsyncSession, device_type_id: int, version: str
) -> Optional[FirmwareVersion]:
    """Get firmware by device_type_id + version."""
    result = await db.execute(
        select(FirmwareVersion).where(
            and_(
                FirmwareVersion.device_type_id == device_type_id,
                FirmwareVersion.version == version,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_firmware(db: AsyncSession, data: FirmwareCreate) -> FirmwareVersion:
    """Create a new firmware version record."""
    # Generate version_display
    version_display = data.version
    if data.git_hash_short:
        version_display = f"{data.version}-{data.git_hash_short}"
    elif data.git_hash:
        version_display = f"{data.version}-{data.git_hash[:7]}"

    firmware = FirmwareVersion(
        **data.model_dump(),
        version_display=version_display,
        released_at=datetime.now(timezone.utc),
    )

    # If marking as latest, unmark other versions of same device type
    if data.is_latest:
        await _unmark_latest(db, data.device_type_id)

    db.add(firmware)
    await db.flush()
    await db.refresh(firmware)
    return firmware


async def update_firmware(
    db: AsyncSession, firmware_id: int, data: FirmwareUpdate
) -> Optional[FirmwareVersion]:
    """Update a firmware version."""
    firmware = await get_firmware(db, firmware_id)
    if not firmware:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # If marking as latest, unmark others first
    if update_data.get("is_latest") is True:
        await _unmark_latest(db, firmware.device_type_id, exclude_id=firmware_id)

    for key, value in update_data.items():
        setattr(firmware, key, value)

    # Regenerate version_display
    git_short = firmware.git_hash_short or (firmware.git_hash[:7] if firmware.git_hash else None)
    if git_short:
        firmware.version_display = f"{firmware.version}-{git_short}"
    else:
        firmware.version_display = firmware.version

    await db.flush()
    await db.refresh(firmware)
    return firmware


async def delete_firmware(db: AsyncSession, firmware_id: int) -> bool:
    """Delete a firmware version."""
    firmware = await get_firmware(db, firmware_id)
    if not firmware:
        return False
    await db.delete(firmware)
    await db.flush()
    return True


async def mark_as_latest(db: AsyncSession, firmware_id: int) -> Optional[FirmwareVersion]:
    """Mark a firmware version as the latest (unmarks others of same type)."""
    firmware = await get_firmware(db, firmware_id)
    if not firmware:
        return None

    await _unmark_latest(db, firmware.device_type_id, exclude_id=firmware_id)
    firmware.is_latest = True
    await db.flush()
    await db.refresh(firmware)
    return firmware


async def mark_as_stable(db: AsyncSession, firmware_id: int) -> Optional[FirmwareVersion]:
    """Mark a firmware version as stable."""
    firmware = await get_firmware(db, firmware_id)
    if not firmware:
        return None

    firmware.is_stable = True
    await db.flush()
    await db.refresh(firmware)
    return firmware


async def _unmark_latest(
    db: AsyncSession, device_type_id: int, exclude_id: Optional[int] = None
) -> None:
    """Unmark all 'latest' firmware for a device type."""
    stmt = (
        update(FirmwareVersion)
        .where(
            and_(
                FirmwareVersion.device_type_id == device_type_id,
                FirmwareVersion.is_latest == True,  # noqa: E712
            )
        )
        .values(is_latest=False)
    )
    if exclude_id:
        stmt = stmt.where(FirmwareVersion.id != exclude_id)
    await db.execute(stmt)
