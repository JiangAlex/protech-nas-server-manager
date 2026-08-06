"""Web UI routes (Jinja2 server-side rendering).

All routes (except login) require session authentication.
"""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_303_SEE_OTHER

from app.config import get_settings
from app.database import get_db
from app.services import device_service
from app.services import firmware_service

settings = get_settings()
templates = Jinja2Templates(directory="app/templates")

router = APIRouter(prefix="/admin", tags=["web"])


# ── Auth helpers ────────────────────────────────────────────


def get_current_user(request: Request) -> str:
    """Check session for authenticated user."""
    username = request.session.get("username")
    if not username:
        raise HTTPException(status_code=303, headers={"Location": "/admin/login"})
    return username


# ── Login / Logout ──────────────────────────────────────────


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Show login form."""
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login."""
    if username == settings.admin_username and password == settings.admin_password:
        request.session["username"] = username
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "帳號或密碼錯誤"}
    )


@router.get("/logout")
async def logout(request: Request):
    """Clear session and redirect to login."""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)


# ── Dashboard ───────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard page - device status overview."""
    device_counts = await device_service.get_device_count_by_status(db)
    devices = await device_service.get_devices(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "counts": device_counts, "devices": devices},
    )


# ── Device pages ────────────────────────────────────────────


@router.get("/devices/", response_class=HTMLResponse)
async def device_list_page(
    request: Request,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Device list page."""
    devices = await device_service.get_devices(db)
    device_types = await device_service.get_device_types(db)
    return templates.TemplateResponse(
        "devices/list.html",
        {"request": request, "user": user, "devices": devices, "device_types": device_types},
    )


@router.get("/devices/{device_id}/", response_class=HTMLResponse)
async def device_detail_page(
    request: Request,
    device_id: int,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Device detail page."""
    device = await device_service.get_device(db, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return templates.TemplateResponse(
        "devices/detail.html",
        {"request": request, "user": user, "device": device},
    )


# ── Device Types page ───────────────────────────────────────


@router.get("/device-types/", response_class=HTMLResponse)
async def device_types_page(
    request: Request,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Device type management page."""
    device_types = await device_service.get_device_types(db)
    return templates.TemplateResponse(
        "device_types/list.html",
        {"request": request, "user": user, "device_types": device_types},
    )


# ── Firmware page ───────────────────────────────────────────


@router.get("/firmware/", response_class=HTMLResponse)
async def firmware_page(
    request: Request,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Firmware version management page."""
    firmware_list = await firmware_service.get_firmware_list(db)
    device_types = await device_service.get_device_types(db)
    return templates.TemplateResponse(
        "firmware/list.html",
        {
            "request": request,
            "user": user,
            "firmware_list": firmware_list,
            "device_types": device_types,
        },
    )


# ── Updates history page ────────────────────────────────────


@router.get("/updates/", response_class=HTMLResponse)
async def updates_page(
    request: Request,
    user: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update history page."""
    from app.models.update_log import UpdateLog
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(UpdateLog)
        .options(selectinload(UpdateLog.device))
        .order_by(UpdateLog.id.desc())
        .limit(100)
    )
    update_logs = list(result.scalars().all())
    return templates.TemplateResponse(
        "updates/list.html",
        {"request": request, "user": user, "update_logs": update_logs},
    )
