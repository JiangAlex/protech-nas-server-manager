"""ESP32 OTA API schemas.

Firmware binary focused - device downloads .bin file and flashes.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Check for update ────────────────────────────────────────


class ESP32CheckResponse(BaseModel):
    """Server responds with firmware update info for ESP32."""
    update_available: bool
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    firmware_url: Optional[str] = None
    file_size: Optional[int] = None
    file_checksum: Optional[str] = None          # SHA-256 of the .bin, hex
    file_signature: Optional[str] = None         # base64 DER ECDSA P-256 signature over that SHA-256
    changelog: Optional[str] = None
    released_at: Optional[datetime] = None
    # Only in the response that enrolled the device: keep it and send it as X-Device-Token
    device_token: Optional[str] = None


# ── Report update result ────────────────────────────────────


class ESP32ReportRequest(BaseModel):
    """ESP32 device reports update result."""
    mac_address: str
    from_version: Optional[str] = None
    to_version: str
    status: str  # completed / failed / rolled_back
    error_message: Optional[str] = None


class ESP32ReportResponse(BaseModel):
    """Server acknowledges the report."""
    success: bool
    message: str
