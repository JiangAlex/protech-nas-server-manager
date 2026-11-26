"""ESP32 OTA API endpoints (device side).

- GET  /api/ota/esp32/check?mac=&version=[&request_token=true]  - Is a newer firmware available?
- GET  /api/ota/esp32/firmware/{version}?mac=                     - Download the firmware binary
- POST /api/ota/esp32/report                                     - Report the update result

Authentication: X-Device-Token (issued once, on the first check with request_token=true), always
required. Rules in app/services/ota_esp32_service.py and device_auth_service.py.
"""

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ota_esp32 import ESP32CheckResponse, ESP32ReportRequest, ESP32ReportResponse
from app.services import ota_esp32_service

router = APIRouter(prefix="/api/ota/esp32", tags=["ota-esp32"])


@router.get("/check", response_model=ESP32CheckResponse)
async def check_update(
    request: Request,
    mac: str = Query(..., description="ESP32 MAC address (registered on the device page)"),
    version: str = Query(..., description="Current firmware version, x.y.z"),
    request_token: bool = Query(False, description="Ask for the device token (first check only)"),
    db: AsyncSession = Depends(get_db),
):
    """ESP32 checks whether a newer firmware is available for its device type."""
    return await ota_esp32_service.check(db, request, mac, version, request_token)


@router.get("/firmware/{version}")
async def download_firmware(
    version: str,
    request: Request,
    mac: str = Query(..., description="ESP32 MAC address"),
    db: AsyncSession = Depends(get_db),
):
    """Download the firmware binary (application image for the OTA partition)."""
    path = await ota_esp32_service.firmware_file(db, request, mac, version)
    return FileResponse(path=str(path), media_type="application/octet-stream", filename=f"firmware-{version}.bin")


@router.post("/report", response_model=ESP32ReportResponse)
async def report_update(body: ESP32ReportRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """ESP32 reports the update result (completed / failed / rolled_back)."""
    return await ota_esp32_service.report(db, request, body)
