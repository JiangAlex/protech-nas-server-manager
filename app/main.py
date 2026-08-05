"""FastAPI application entry point.

Initializes the app, registers routers, configures middleware,
manages lifespan events (DB connection, scheduler startup/shutdown).
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine

logger = structlog.get_logger()


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})
