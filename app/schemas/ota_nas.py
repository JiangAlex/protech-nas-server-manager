"""NAS OTA API schemas.

Systemd deployment focused - git pull + pip install + restart service + frontend artifact download.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ── Check for update ────────────────────────────────────────


class NASCheckRequest(BaseModel):
    """NAS device sends current version info to check for updates."""
    device_id: int
    current_version: Optional[str] = None
    current_git_hash: Optional[str] = None
    mac_address: Optional[str] = None
    deploy_mode: str = "systemd"


class NASCheckResponse(BaseModel):
    """Server responds with update availability."""
    update_available: bool
    current_version: Optional[str] = None
    latest_version: Optional[str] = None
    latest_git_hash: Optional[str] = None
    changelog: Optional[str] = None
    download_url: Optional[str] = None
    frontend_artifact_url: Optional[str] = None
    released_at: Optional[datetime] = None


# ── Download info ───────────────────────────────────────────


class NASDownloadInfo(BaseModel):
    """Update download/execution information for NAS device."""
    version: str
    git_hash: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = None
    deploy_mode: str = "systemd"
    frontend_artifact_url: Optional[str] = None
    frontend_checksum: Optional[str] = None
    instructions: Optional[str] = None


# ── Report update result ────────────────────────────────────


class NASReportRequest(BaseModel):
    """NAS device reports update result back to server."""
    device_id: int
    from_version: Optional[str] = None
    to_version: str
    to_git_hash: Optional[str] = None
    status: str  # completed / failed / rolled_back
    error_message: Optional[str] = None


class NASReportResponse(BaseModel):
    """Server acknowledges the report."""
    success: bool
    message: str
