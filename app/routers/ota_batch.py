"""Batch OTA update API endpoints (群發更新).

- POST /api/ota/batch/push          - Push update to selected devices
- GET  /api/ota/batch/status         - Get batch update progress
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.device import Device
from app.models.firmware import FirmwareVersion

router = APIRouter(prefix="/api/ota/batch", tags=["ota-batch"])


class BatchPushRequest(BaseModel):
    """Request to push update to multiple devices."""

    firmware_id: int

    # Target selection (at least one filter required)
    device_ids: Optional[list[int]] = None  # Specific devices
    sku: Optional[str] = None  # All devices with this SKU
    customer_id: Optional[str] = None  # All devices for this customer
    device_type_id: Optional[int] = None  # All devices of this type
    all_devices: bool = False  # Push to ALL active devices


class BatchPushResponse(BaseModel):
    """Response with batch push results."""

    success: bool
    message: str
    total_devices: int
    targeted_devices: list[dict]


@router.post("/push", response_model=BatchPushResponse)
async def batch_push_update(request: BatchPushRequest, db: AsyncSession = Depends(get_db)):
    """Push a firmware version to multiple devices (群發更新).

    Targets devices by:
    - device_ids: specific device IDs
    - sku: all devices with matching SKU
    - customer_id: all devices for a customer
    - device_type_id: all devices of a type
    - all_devices: every active device

    This marks the firmware as the target for selected devices.
    Devices will pick up the update on their next check-in.
    """
    # Validate firmware exists
    firmware = await db.get(FirmwareVersion, request.firmware_id)
    if not firmware:
        raise HTTPException(status_code=404, detail="Firmware version not found")

    # Build device query
    conditions = [Device.is_active == True]  # noqa: E712

    if request.device_ids:
        conditions.append(Device.id.in_(request.device_ids))
    elif request.sku:
        conditions.append(Device.sku == request.sku)
    elif request.customer_id:
        conditions.append(Device.customer_id == request.customer_id)
    elif request.device_type_id:
        conditions.append(Device.device_type_id == request.device_type_id)
    elif request.all_devices:
        # No additional filter — all active devices
        pass
    else:
        raise HTTPException(
            status_code=400,
            detail="Must specify at least one target: device_ids, sku, customer_id, device_type_id, or all_devices=true",
        )

    result = await db.execute(select(Device).where(and_(*conditions)))
    devices = result.scalars().all()

    if not devices:
        return BatchPushResponse(
            success=False,
            message="No matching devices found",
            total_devices=0,
            targeted_devices=[],
        )

    # Mark firmware as latest for the device type (so devices pick it up on next check)
    # Reset previous latest
    prev_result = await db.execute(
        select(FirmwareVersion).where(
            and_(
                FirmwareVersion.device_type_id == firmware.device_type_id,
                FirmwareVersion.is_latest == True,  # noqa: E712
                FirmwareVersion.id != firmware.id,
            )
        )
    )
    for prev in prev_result.scalars().all():
        prev.is_latest = False

    firmware.is_latest = True
    firmware.is_stable = True

    await db.commit()

    targeted = [
        {
            "id": d.id,
            "name": d.name,
            "sku": d.sku,
            "customer_id": d.customer_id,
            "mac_address": d.mac_address,
            "current_version": d.current_version,
            "status": d.status,
        }
        for d in devices
    ]

    return BatchPushResponse(
        success=True,
        message=f"Firmware {firmware.version} targeted to {len(devices)} device(s). They will update on next check-in.",
        total_devices=len(devices),
        targeted_devices=targeted,
    )


@router.get("/status")
async def batch_status(
    sku: Optional[str] = None,
    customer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get update status of devices (by SKU or customer).

    Shows which devices have updated and which are still pending.
    """
    conditions = [Device.is_active == True]  # noqa: E712

    if sku:
        conditions.append(Device.sku == sku)
    if customer_id:
        conditions.append(Device.customer_id == customer_id)

    result = await db.execute(select(Device).where(and_(*conditions)))
    devices = result.scalars().all()

    # Get latest firmware for comparison
    device_type_ids = set(d.device_type_id for d in devices)
    latest_versions = {}
    for dt_id in device_type_ids:
        fw_result = await db.execute(
            select(FirmwareVersion).where(
                and_(
                    FirmwareVersion.device_type_id == dt_id,
                    FirmwareVersion.is_latest == True,  # noqa: E712
                )
            ).limit(1)
        )
        fw = fw_result.scalar_one_or_none()
        if fw:
            latest_versions[dt_id] = fw

    status_list = []
    for d in devices:
        latest_fw = latest_versions.get(d.device_type_id)
        is_up_to_date = False
        if latest_fw:
            version_match = d.current_version == latest_fw.version
            hash_match = (
                d.current_git_hash and latest_fw.git_hash
                and d.current_git_hash in latest_fw.git_hash
            ) if d.current_git_hash and latest_fw.git_hash else True
            is_up_to_date = version_match and hash_match

        status_list.append({
            "id": d.id,
            "name": d.name,
            "sku": d.sku,
            "customer_id": d.customer_id,
            "mac_address": d.mac_address,
            "current_version": d.current_version,
            "current_git_hash": d.current_git_hash,
            "target_version": latest_fw.version if latest_fw else None,
            "target_git_hash": latest_fw.git_hash if latest_fw else None,
            "is_up_to_date": is_up_to_date,
            "status": d.status,
            "last_seen_at": d.last_seen_at,
            "last_update_at": d.last_update_at,
        })

    up_to_date = sum(1 for s in status_list if s["is_up_to_date"])
    pending = len(status_list) - up_to_date

    return {
        "total": len(status_list),
        "up_to_date": up_to_date,
        "pending": pending,
        "devices": status_list,
    }
