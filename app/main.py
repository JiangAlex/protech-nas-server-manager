"""FastAPI application entry point.

Initializes the app, registers routers, configures middleware,
manages lifespan events (DB connection, scheduler startup/shutdown).
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import engine
from app.services.scheduler import start_scheduler, stop_scheduler

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup: verify DB connection
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connected")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        raise

    # Known defaults from config.py are public (the repository is on GitHub): anyone could sign a
    # session cookie with the default secret, or log in with the default password
    if settings.session_secret_key == "change-this-to-a-random-secret-key":
        logger.error("insecure_default_session_secret", hint="set SESSION_SECRET_KEY in .env")
    if settings.admin_password == "change-me-in-production":
        logger.error("insecure_default_admin_password", hint="set ADMIN_PASSWORD in .env")
    if not settings.device_token_enforce:
        logger.warning("device_token_transition_mode", hint="DEVICE_TOKEN_ENFORCE=true once all devices have tokens")

    # Start scheduler
    start_scheduler()

    yield

    # Shutdown: stop scheduler and dispose engine
    stop_scheduler()
    await engine.dispose()
    logger.info("database_disconnected")


app = FastAPI(
    title="Protech NAS Server Manager",
    description="管理多台 Protech NAS 設備的軟體版本、推送更新、監控狀態",
    version="0.1.0",
    lifespan=lifespan,
    # The server is reachable from the internet: no public API description unless ENABLE_API_DOCS=true
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None,
    openapi_url="/openapi.json" if settings.enable_api_docs else None,
)

# Session middleware for web admin auth
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register API routers
from app.routers.device_types import router as device_types_router  # noqa: E402
from app.routers.devices import router as devices_router  # noqa: E402
from app.routers.firmware import router as firmware_router  # noqa: E402
from app.routers.ota_nas import router as ota_nas_router  # noqa: E402
from app.routers.ota_esp32 import router as ota_esp32_router  # noqa: E402
from app.routers.tiles import router as tiles_router  # noqa: E402
from app.routers.ota_batch import router as ota_batch_router  # noqa: E402
from app.routers.web import router as web_router  # noqa: E402
from app.routers.metrics import router as metrics_router  # noqa: E402
from app.routers.dashboard import router as dashboard_router  # noqa: E402
from app.auth import require_admin  # noqa: E402

# Admin API: web login session or X-API-Key (app/auth.py)
admin_only = [Depends(require_admin)]
app.include_router(device_types_router, dependencies=admin_only)
app.include_router(devices_router, dependencies=admin_only)
app.include_router(firmware_router, dependencies=admin_only)
app.include_router(ota_batch_router, dependencies=admin_only)
app.include_router(metrics_router, dependencies=admin_only)
app.include_router(dashboard_router, dependencies=admin_only)
# Device endpoints: per-device tokens (app/services/device_auth_service.py); ESP32 OTA is still a placeholder
app.include_router(ota_nas_router)
app.include_router(ota_esp32_router)
app.include_router(tiles_router)
# Web pages: their own login check (app/routers/web.py)
app.include_router(web_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})
