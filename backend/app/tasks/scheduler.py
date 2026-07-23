"""Time-based scheduler - replaces v1's single cron with slot-aware intervals."""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, time as dt_time, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ..config import AppConfig, ScheduleSlot
from ..utils.logger import get_logger

logger = get_logger("scheduler")


def _now_time() -> dt_time:
    return datetime.now(timezone.utc).timetz()


def _slot_for(schedule: list[ScheduleSlot], t: dt_time) -> ScheduleSlot | None:
    """Return the active ScheduleSlot for the given time, or None."""
    for slot in schedule:
        try:
            s = dt_time.fromisoformat(slot.start)
            e = dt_time.fromisoformat(slot.end)
            if s <= e:
                active = s <= t < e
            else:
                active = t >= s or t < e
            if active:
                return slot
        except Exception:
            continue
    return None


class TimeBasedScheduler:
    """
    Drives fetch_task based on config.yaml schedule slots.

    During active slots (e.g. 06:00-10:00), runs every `interval_minutes`
    with random jitter.  Outside slots, sleeps 1h and re-checks.
    """

    def __init__(self, config: AppConfig, fetch_task_fn):
        self.config = config
        self.fetch_task_fn = fetch_task_fn  # async callable(db, config)
        self.schedule = config.fetch.schedule or []
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("TimeBasedScheduler started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("TimeBasedScheduler stopped")

    async def _run_loop(self) -> None:
        while self._running:
            t = _now_time()
            slot = _slot_for(self.schedule, t)

            if slot:
                interval_s = slot.interval_minutes * 60
                jitter = random.uniform(0, self.config.fetch.jitter_seconds)
                sleep = interval_s + jitter
                logger.info(f"In slot {slot.start}-{slot.end}: next run in {sleep:.0f}s")
                await asyncio.sleep(sleep)
                if not self._running:
                    break
                try:
                    await self._run_fetch()
                except Exception as e:
                    logger.error(f"Scheduled fetch failed: {e}")
            else:
                # Not in any active slot: sleep 1h and re-check
                logger.info("Outside all active slots, sleeping 1h before re-checking")
                await asyncio.sleep(3600)

    async def _run_fetch(self) -> None:
        from app.database import get_engine, get_session_factory
        engine = get_engine(self.config)
        SF = get_session_factory(engine)
        db = SF()
        try:
            logger.info("Scheduled fetch starting")
            results = await self.fetch_task_fn(db, self.config)
            inserted = sum(r.get("inserted", 0) for r in results)
            logger.info(f"Scheduled fetch done: inserted={inserted} total={len(results)} sources")
        except Exception as e:
            logger.error(f"fetch_task_fn failed: {e}")
            raise
        finally:
            db.close()


class LegacyScheduler:
    """
    Thin wrapper over apscheduler for simple cron-based tasks
    (used for cleanup_task which is just "0 5 * * *").
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self._scheduler = AsyncIOScheduler()

    def add_cron(self, cron_expr: str, func, *args, **kwargs) -> None:
        parts = cron_expr.split()
        if len(parts) != 5:
            logger.warning(f"Invalid cron: {cron_expr}")
            return
        trigger = CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4])
        self._scheduler.add_job(func, trigger, args=args, kwargs=kwargs, misfire_grace_time=3600)
        logger.info(f"Added cron job: {cron_expr} -> {func.__name__}")

    def start(self) -> None:
        self._scheduler.start()
        logger.info("LegacyScheduler (apscheduler) started")

    def shutdown(self, wait: bool = True) -> None:
        self._scheduler.shutdown(wait=wait)
        logger.info("LegacyScheduler shutdown")