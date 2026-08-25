"""APScheduler configuration for periodic tasks.

Scheduled jobs:
- Metrics collection: every 5 minutes for all active devices
- Health check: Runs every N seconds, checks all active devices
- Offline detection: Evaluates last_seen_at vs threshold
"""

import asyncio
from datetime import datetime, timezone

import structlog
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.device import Device
from app.services.metrics_service import collect_device_metrics, save_metrics_snapshot

logger = structlog.get_logger()

_scheduler = None


def _get_scheduler():
    """Lazy-init APScheduler singleton."""
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler

        _scheduler = AsyncIOScheduler()
    return _scheduler


async def _collect_all_metrics() -> None:
    """Collect metrics from all active devices and store snapshots.

    Runs every 5 minutes via APScheduler.
    """
    logger.info("metrics_collection_job_started")
    try:
        async with async_session_factory() as db:
            stmt = select(Device).where(Device.is_active == True)
            result = await db.execute(stmt)
            devices = result.scalars().all()

        collected = 0
        failed = 0
        for device in devices:
            metrics = await collect_device_metrics(device)
            if metrics is None:
                failed += 1
                continue
            async with async_session_factory() as db:
                await save_metrics_snapshot(db, device.id, metrics)
                await db.commit()
            collected += 1

        logger.info(
            "metrics_collection_job_finished",
            collected=collected,
            failed=failed,
            total=len(devices),
        )
    except Exception as e:
        logger.error("metrics_collection_job_error", error=str(e))


def start_scheduler() -> None:
    """Register all scheduled jobs and start the scheduler.

    Call from the FastAPI lifespan startup handler.
    """
    sched = _get_scheduler()

    # Metrics collection every 5 minutes
    sched.add_job(
        _collect_all_metrics,
        trigger=IntervalTrigger(minutes=5),
        id="collect_all_metrics",
        name="Collect metrics from all active DUTs",
        replace_existing=True,
    )

    sched.start()
    logger.info("scheduler_started", jobs=len(sched.get_jobs()))


def stop_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler_stopped")
