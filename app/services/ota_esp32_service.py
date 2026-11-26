"""ESP32 OTA: check, firmware download, report.

The device is found by its MAC. An admin registers the device (with the MAC) first; an unknown MAC
gets "no update" and an unknown_device entry in the log. The device asks for its token on its first
check (request_token=true); after that every request needs X-Device-Token. There is no transition
mode for ESP32: a missing token is always rejected (the firmware client always has token support).

Releases: the latest + stable firmware record of the device's type that has a binary
(POST /api/firmware/{id}/binary). It is offered only when its version is higher than the device's
("x.y.z" compared as numbers), so a device ahead of the release is never sent back.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog
from fastapi import HTTPException, Request
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.firmware import FirmwareVersion
from app.models.update_log import UpdateLog
from app.schemas.ota_esp32 import ESP32CheckResponse, ESP32ReportRequest, ESP32ReportResponse
from app.services import device_auth_service, firmware_file_service, version_util

logger = structlog.get_logger()


async def find_device(db: AsyncSession, mac: str) -> Optional[Device]:
    m = device_auth_service.normalize_mac(mac)
    if not m:
        return None
    result = await db.execute(
        select(Device).where(func.lower(Device.mac_address) == m, Device.is_active == True)  # noqa: E712
    )
    return result.scalars().first()


async def _device_or_log(db: AsyncSession, http: Request, mac: str, endpoint: str) -> Optional[Device]:
    device = await find_device(db, mac)
    if device is None:
        await device_auth_service.log_event(db, http, None, "unknown_device", endpoint, mac, f"mac {mac}")
    return device


async def latest_release(db: AsyncSession, device_type_id: int) -> Optional[FirmwareVersion]:
    result = await db.execute(
        select(FirmwareVersion).where(
            and_(
                FirmwareVersion.device_type_id == device_type_id,
                FirmwareVersion.is_latest == True,  # noqa: E712
                FirmwareVersion.is_stable == True,  # noqa: E712
                FirmwareVersion.file_path.is_not(None),
            )
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def check(db: AsyncSession, http: Request, mac: str, version: str, request_token: bool) -> ESP32CheckResponse:
    no_update = ESP32CheckResponse(update_available=False, current_version=version, latest_version=version)
    device = await _device_or_log(db, http, mac, "esp32_check")
    if device is None:
        return no_update
    auth = await device_auth_service.authenticate(
        db, http, device, "esp32_check", request_token=request_token, mac=mac, enforce=True
    )
    device.last_seen_at = datetime.now(timezone.utc)
    device.status = "online"
    if version_util.parse(version):
        device.current_version = version

    release = await latest_release(db, device.device_type_id)
    resp = ESP32CheckResponse(
        update_available=False, current_version=version,
        latest_version=release.version if release else version, device_token=auth.issued_token,
    )
    if release and firmware_file_service.stored_file(release.file_path) and version_util.is_newer(release.version, version):
        resp.update_available = True
        resp.firmware_url = f"/api/ota/esp32/firmware/{release.version}"
        resp.file_size = release.file_size
        resp.file_checksum = release.file_checksum
        resp.file_signature = release.file_signature
        resp.changelog = release.changelog
        resp.released_at = release.released_at
    return resp


async def firmware_file(db: AsyncSession, http: Request, mac: str, version: str) -> Path:
    device = await _device_or_log(db, http, mac, "esp32_download")
    if device is None:
        raise HTTPException(status_code=404, detail="Unknown device")
    await device_auth_service.authenticate(db, http, device, "esp32_download", mac=mac, enforce=True)
    result = await db.execute(
        select(FirmwareVersion).where(
            and_(FirmwareVersion.device_type_id == device.device_type_id, FirmwareVersion.version == version)
        ).limit(1)
    )
    fw = result.scalar_one_or_none()
    path = firmware_file_service.stored_file(fw.file_path) if fw else None
    if path is None:
        raise HTTPException(status_code=404, detail=f"No firmware binary {version} for this device")
    logger.info("esp32_firmware_download", device_id=device.id, version=version)
    return path


async def report(db: AsyncSession, http: Request, body: ESP32ReportRequest) -> ESP32ReportResponse:
    device = await _device_or_log(db, http, body.mac_address, "esp32_report")
    if device is None:
        return ESP32ReportResponse(success=False, message="Unknown device")
    await device_auth_service.authenticate(db, http, device, "esp32_report", mac=body.mac_address, enforce=True)
    now = datetime.now(timezone.utc)
    device.last_seen_at = now
    device.status = "online"
    if body.status == "completed":
        device.current_version = body.to_version
        device.last_update_at = now
    db.add(UpdateLog(
        device_id=device.id, from_version=body.from_version, to_version=body.to_version,
        status=body.status, triggered_by="device", error_message=body.error_message,
        started_at=now, completed_at=now,
    ))
    logger.info("esp32_ota_report", device_id=device.id, status=body.status, to_version=body.to_version)
    return ESP32ReportResponse(success=True, message=f"Update report recorded: {body.status}")
