"""ESP32 OTA API endpoints.

- GET  /api/ota/esp32/check              - ESP32 checks for new firmware
- GET  /api/ota/esp32/firmware/{version}  - Download firmware binary
- POST /api/ota/esp32/report             - ESP32 reports update result

Authentication: X-Device-Token header (TODO)
"""

from fastapi import APIRouter, Header, HTTPException, Query
from fastapi.responses import JSONResponse

from app.schemas.ota_esp32 import (
    ESP32CheckResponse,
    ESP32ReportRequest,
    ESP32ReportResponse,
)

router = APIRouter(prefix="/api/ota/esp32", tags=["ota-esp32"])


@router.get("/check", response_model=ESP32CheckResponse)
async def check_update(
    mac: str = Query(..., description="ESP32 MAC address"),
    version: str = Query(..., description="Current firmware version"),
    x_device_token: str = Header(None, alias="X-Device-Token"),
):
    """ESP32 checks if a new firmware is available.

    TODO: Implement firmware version lookup and device token validation.
    """
    # Placeholder - always returns no update
    return ESP32CheckResponse(
        update_available=False,
        current_version=version,
        latest_version=version,
    )


@router.get("/firmware/{version}")
async def download_firmware(version: str):
    """Download firmware binary for ESP32.

    TODO: Implement firmware file serving from storage.
    """
    raise HTTPException(status_code=501, detail="ESP32 firmware download not yet implemented")


@router.post("/report", response_model=ESP32ReportResponse)
async def report_update(request: ESP32ReportRequest):
    """ESP32 reports update result.

    TODO: Implement device lookup by MAC address and update logging.
    """
    # Placeholder - acknowledge receipt
    return ESP32ReportResponse(
        success=True,
        message=f"Report received for {request.mac_address}: {request.status}",
    )
