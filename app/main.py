"""FastAPI application entry point.

Initializes the app, registers routers, configures middleware,
manages lifespan events (DB connection, scheduler startup/shutdown).
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import engine

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

    yield

    # Shutdown: dispose engine
    await engine.dispose()
    logger.info("database_disconnected")


app = FastAPI(
    title="Protech NAS Server Manager",
    description="管理多台 Protech NAS 設備的軟體版本、推送更新、監控狀態",
    version="0.1.0",
    lifespan=lifespan,
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
from app.routers.ota_batch import router as ota_batch_router  # noqa: E402
from app.routers.web import router as web_router  # noqa: E402

app.include_router(device_types_router)
app.include_router(devices_router)
app.include_router(firmware_router)
app.include_router(ota_nas_router)
app.include_router(ota_esp32_router)
app.include_router(ota_batch_router)
app.include_router(web_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})
