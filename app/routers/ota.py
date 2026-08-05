"""OTA API endpoints for NAS and firmware devices.

- POST /api/ota/check         - Device checks for new version
- GET  /api/ota/download/{id} - Get update download/instructions
- POST /api/ota/report        - Device reports update result
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ota import (
    OTACheckRequest,
    OTACheckResponse,
    OTADownloadInfo,
    OTAReportRequest,
    OTAReportResponse,
)
from app.services import ota_service

router = APIRouter(prefix="/api/ota", tags=["ota"])


@router.post("/check", response_model=OTACheckResponse)
async def check_update(request: OTACheckRequest, db: AsyncSession = Depends(get_db)):
    """Device checks if a new version is available.

    NAS sends its current version, server compares with latest firmware
    and returns whether an update is available.
    """
    return await ota_service.check_update(db, request)


@router.get("/download/{device_id}", response_model=OTADownloadInfo)
async def get_download_info(device_id: int, db: AsyncSession = Depends(get_db)):
    """Get update download information and instructions.

    Returns git repo URL, branch, hash, and shell instructions
    for the device to execute the update.
    """
    info = await ota_service.get_download_info(db, device_id)
    if not info:
        raise HTTPException(status_code=404, detail="No update available for this device")
    return info


@router.post("/report", response_model=OTAReportResponse)
async def report_update(request: OTAReportRequest, db: AsyncSession = Depends(get_db)):
    """Device reports update result (success/failure/rollback).

    Server logs the result and updates device status accordingly.
    """
    return await ota_service.report_update(db, request)
