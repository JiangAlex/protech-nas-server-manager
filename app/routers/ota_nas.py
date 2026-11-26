"""NAS OTA API endpoints.

- POST /api/ota/nas/check                          - NAS checks for new version
- GET  /api/ota/nas/download/{device_id}           - Get update instructions
- GET  /api/ota/nas/artifacts/{version}/frontend.tar.gz - Download frontend artifact
- POST /api/ota/nas/artifacts/{version}/upload     - Upload frontend artifact (admin)
- POST /api/ota/nas/report                         - NAS reports update result

check, download and report take the device token (X-Device-Token, see device_auth_service);
the artifact upload needs the admin login or X-API-Key.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db
from app.models.device import Device
from app.schemas.ota_nas import (
    NASCheckRequest,
    NASCheckResponse,
    NASDownloadInfo,
    NASReportRequest,
    NASReportResponse,
)
from app.services import artifact_service, device_auth_service, ota_nas_service

router = APIRouter(prefix="/api/ota/nas", tags=["ota-nas"])


@router.post("/check", response_model=NASCheckResponse)
async def check_update(body: NASCheckRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """NAS device checks if a new version is available.

    Device sends its current version, server compares with latest firmware
    and returns whether an update is available along with frontend artifact URL.
    With "request_token": true a device without a token gets one (device_token, sent once).
    """
    return await ota_nas_service.check_update(db, body, request)


@router.get("/download/{device_id}", response_model=NASDownloadInfo)
async def get_download_info(device_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """Get update download information and systemd instructions.

    Returns git info, shell instructions for backend update,
    and frontend artifact download URL + checksum.
    """
    device = await db.get(Device, device_id)
    if device:
        await device_auth_service.authenticate(db, request, device, "download")
    info = await ota_nas_service.get_download_info(db, device_id)
    if not info:
        raise HTTPException(status_code=404, detail="No update available for this device")
    return info


@router.get("/artifacts/{version}/frontend.tar.gz")
async def download_artifact(version: str):
    """Download pre-built frontend artifact.

    NAS devices download this to deploy frontend without needing Node.js.
    """
    if not artifact_service.artifact_exists(version):
        raise HTTPException(status_code=404, detail=f"Artifact not found for version {version}")

    file_path = artifact_service.get_artifact_path(version)
    return FileResponse(
        path=str(file_path),
        media_type="application/gzip",
        filename="frontend.tar.gz",
    )


@router.post("/artifacts/{version}/upload", dependencies=[Depends(require_admin)])
async def upload_artifact(version: str, file: UploadFile = File(...)):
    """Upload frontend.tar.gz artifact for a version.

    Called by CI/CD or admin to upload pre-built frontend.
    """
    if not file.filename or not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="File must be .tar.gz or .tgz")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    checksum, file_size = await artifact_service.save_artifact(version, content)

    return {
        "version": version,
        "filename": "frontend.tar.gz",
        "size": file_size,
        "checksum": checksum,
    }


@router.post("/report", response_model=NASReportResponse)
async def report_update(body: NASReportRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """NAS device reports update result (success/failure/rollback).

    Server logs the result and updates device status accordingly.
    """
    device = await db.get(Device, body.device_id)
    if device:
        await device_auth_service.authenticate(db, request, device, "report")
    return await ota_nas_service.report_update(db, body)
