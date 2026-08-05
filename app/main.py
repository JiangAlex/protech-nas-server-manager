"""FastAPI application entry point.

Initializes the app, registers routers, configures middleware,
manages lifespan events (DB connection, scheduler startup/shutdown).
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Protech NAS Server Manager",
    description="管理多台 Protech NAS 設備的軟體版本、推送更新、監控狀態",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "ok"})
