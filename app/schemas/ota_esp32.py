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
    file_checksum: Optional[str] = None
    changelog: Optional[str] = None
    released_at: Optional[datetime] = None


# ── Report update result ────────────────────────────────────


class ESP32ReportRequest(BaseModel):
    """ESP32 device reports update result."""
    mac_address: str
    from_version: Optional[str] = None
    to_version: str
    status: str  # completed / failed
    error_message: Optional[str] = None


class ESP32ReportResponse(BaseModel):
    """Server acknowledges the report."""
    success: bool
    message: str
