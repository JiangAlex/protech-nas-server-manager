"""Firmware version management schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class FirmwareCreate(BaseModel):
    device_type_id: int
    version: str
    git_hash: Optional[str] = None
    git_hash_short: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = "main"
    changelog: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_checksum: Optional[str] = None
    frontend_artifact_path: Optional[str] = None
    frontend_checksum: Optional[str] = None
    is_latest: bool = False
    is_stable: bool = False


class FirmwareUpdate(BaseModel):
    version: Optional[str] = None
    git_hash: Optional[str] = None
    git_hash_short: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = None
    changelog: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_checksum: Optional[str] = None
    frontend_artifact_path: Optional[str] = None
    frontend_checksum: Optional[str] = None
    is_latest: Optional[bool] = None
    is_stable: Optional[bool] = None


class FirmwareResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_type_id: int
    version: str
    git_hash: Optional[str] = None
    git_hash_short: Optional[str] = None
    version_display: Optional[str] = None
    git_repo_url: Optional[str] = None
    git_branch: Optional[str] = None
    changelog: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    file_checksum: Optional[str] = None
    frontend_artifact_path: Optional[str] = None
    frontend_checksum: Optional[str] = None
    is_latest: bool
    is_stable: bool
    released_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
