"""NAS OTA service logic.

Handles update checking, download info with systemd instructions,
frontend artifact info, and report processing.
"""

from datetime import datetime, timezone
from typing import Optional

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.firmware import FirmwareVersion
from app.models.update_log import UpdateLog
from app.schemas.ota_nas import (
    NASCheckRequest,
    NASCheckResponse,
    NASDownloadInfo,
    NASReportRequest,
    NASReportResponse,
)
from app.services import artifact_service

logger = structlog.get_logger()


async def check_update(db: AsyncSession, request: NASCheckRequest) -> NASCheckResponse:
    """Check if an update is available for the NAS device."""

    device = await db.get(Device, request.device_id)
    if not device:
        return NASCheckResponse(
            update_available=False,
            current_version=request.current_version,
        )

    # Update device status
    device.last_seen_at = datetime.now(timezone.utc)
    device.status = "online"
    if request.current_version:
        device.current_version = request.current_version
    if request.current_git_hash:
        device.current_git_hash = request.current_git_hash
    if request.deploy_mode:
        device.deploy_mode = request.deploy_mode

    # Find latest stable firmware for this device type
    result = await db.execute(
        select(FirmwareVersion)
        .where(
            and_(
                FirmwareVersion.device_type_id == device.device_type_id,
                FirmwareVersion.is_latest == True,  # noqa: E712
                FirmwareVersion.is_stable == True,  # noqa: E712
            )
        )
        .limit(1)
    )
    latest_firmware = result.scalar_one_or_none()

    if not latest_firmware:
        return NASCheckResponse(
            update_available=False,
            current_version=request.current_version,
        )

    # Compare versions
    current = request.current_version or device.current_version
    if current == latest_firmware.version:
        return NASCheckResponse(
            update_available=False,
            current_version=current,
            latest_version=latest_firmware.version,
        )

    # Build frontend artifact URL if available
    frontend_url = None
    if artifact_service.artifact_exists(latest_firmware.version):
        frontend_url = f"/api/ota/nas/artifacts/{latest_firmware.version}/frontend.tar.gz"

    return NASCheckResponse(
        update_available=True,
        current_version=current,
        latest_version=latest_firmware.version,
        latest_git_hash=latest_firmware.git_hash,
        changelog=latest_firmware.changelog,
        download_url=f"/api/ota/nas/download/{device.id}",
        frontend_artifact_url=frontend_url,
        released_at=latest_firmware.released_at,
    )


async def get_download_info(db: AsyncSession, device_id: int) -> Optional[NASDownloadInfo]:
    """Get download/update instructions for a NAS device (systemd mode)."""

    device = await db.get(Device, device_id)
    if not device:
        return None

    # Find latest stable firmware
    result = await db.execute(
        select(FirmwareVersion)
        .where(
            and_(
                FirmwareVersion.device_type_id == device.device_type_id,
                FirmwareVersion.is_latest == True,  # noqa: E712
                FirmwareVersion.is_stable == True,  # noqa: E712
            )
        )
        .limit(1)
    )
    latest_firmware = result.scalar_one_or_none()

    if not latest_firmware:
        return None

    # Build systemd update instructions
    git_branch = latest_firmware.git_branch or "main"
    git_hash = latest_firmware.git_hash or git_branch

    instructions = (
        f"cd /opt/protech-nas && "
        f"git fetch origin {git_branch} && "
        f"git checkout {git_hash} && "
        f"cd backend && source .venv/bin/activate && "
        f"pip install -r requirements.txt && "
        f"sudo systemctl restart protech-nas"
    )

    # Frontend artifact info
    frontend_url = None
    frontend_checksum = None
    if artifact_service.artifact_exists(latest_firmware.version):
        frontend_url = f"/api/ota/nas/artifacts/{latest_firmware.version}/frontend.tar.gz"
        frontend_checksum = latest_firmware.frontend_checksum or artifact_service.get_artifact_checksum(
            latest_firmware.version
        )

    return NASDownloadInfo(
        version=latest_firmware.version,
        git_hash=latest_firmware.git_hash,
        git_repo_url=latest_firmware.git_repo_url,
        git_branch=git_branch,
        deploy_mode=device.deploy_mode,
        frontend_artifact_url=frontend_url,
        frontend_checksum=frontend_checksum,
        instructions=instructions,
    )


async def report_update(db: AsyncSession, request: NASReportRequest) -> NASReportResponse:
    """Process update report from NAS device."""

    device = await db.get(Device, request.device_id)
    if not device:
        return NASReportResponse(success=False, message="Device not found")

    # Update device info
    device.last_seen_at = datetime.now(timezone.utc)
    device.status = "online"

    if request.status == "completed":
        device.current_version = request.to_version
        device.current_git_hash = request.to_git_hash
        device.last_update_at = datetime.now(timezone.utc)

    # Create update log entry
    update_log = UpdateLog(
        device_id=request.device_id,
        from_version=request.from_version,
        to_version=request.to_version,
        to_git_hash=request.to_git_hash,
        status=request.status,
        triggered_by="device",
        error_message=request.error_message,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db.add(update_log)

    logger.info(
        "nas_ota_report",
        device_id=request.device_id,
        device_name=device.name,
        status=request.status,
        to_version=request.to_version,
    )

    return NASReportResponse(
        success=True,
        message=f"Update report recorded: {request.status}",
    )
