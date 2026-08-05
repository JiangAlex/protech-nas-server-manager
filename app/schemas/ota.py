"""OTA API schemas for device update check/download/report."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Check for update ────────────────────────────────────────


class OTACheckRequest(BaseModel):
    """Device sends current version info to check for updates."""
    device_id: int
    current_version: Optional[str] = None
    current_git_hash: Optional[str] = None
    device_type: Optional[str] = None  # fallback if device_id not registered


class OTACheckResponse(BaseModel):
    """Server responds with update availability."""
    update_available: bool
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    latest_git_hash: Optional[str] = None
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    file_size: Optional[int] = None
    file_checksum: Optional[str] = None
    released_at: Optional[datetime] = None


# ── Download update ─────────────────────────────────────────


class OTADownloadInfo(BaseModel):
    """Update download information."""
    version: str
    git_hash: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = None
    file_url: Optional[str] = None
    file_checksum: Optional[str] = None
    instructions: Optional[str] = None  # e.g., "git pull && docker compose up -d --build"


# ── Report update result ────────────────────────────────────


class OTAReportRequest(BaseModel):
    """Device reports update result back to server."""
    device_id: int
    from_version: Optional[str] = None
    to_version: str
    to_git_hash: Optional[str] = None
    status: str  # completed / failed / rolled_back
    error_message: Optional[str] = None


class OTAReportResponse(BaseModel):
    """Server acknowledges the report."""
    success: bool
    message: str
