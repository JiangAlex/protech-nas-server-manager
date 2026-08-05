"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── DeviceType schemas ──────────────────────────────────────


class DeviceTypeCreate(BaseModel):
    name: str
    display_name: str
    update_method: str = "git_pull"
    health_check_method: str = "http"
    config: Optional[dict] = None


class DeviceTypeUpdate(BaseModel):
    display_name: Optional[str] = None
    update_method: Optional[str] = None
    health_check_method: Optional[str] = None
    config: Optional[dict] = None


class DeviceTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    update_method: str
    health_check_method: str
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


# ── Device schemas ──────────────────────────────────────────


class DeviceCreate(BaseModel):
    device_type_id: int
    name: str
    description: Optional[str] = None
    is_active: bool = True
    ip_address: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: int = 22
    ssh_user: Optional[str] = None
    config: Optional[dict] = None


class DeviceUpdate(BaseModel):
    device_type_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    ip_address: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_user: Optional[str] = None
    config: Optional[dict] = None


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_type_id: int
    name: str
    description: Optional[str] = None
    is_active: bool
    current_version: Optional[str] = None
    current_git_hash: Optional[str] = None
    ip_address: Optional[str] = None
    ssh_host: Optional[str] = None
    ssh_port: int
    ssh_user: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    last_update_at: Optional[datetime] = None
    status: str
    config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class DeviceListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    device_type_id: int
    is_active: bool
    current_version: Optional[str] = None
    ip_address: Optional[str] = None
    status: str
    last_seen_at: Optional[datetime] = None
