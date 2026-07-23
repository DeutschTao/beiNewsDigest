"""Manual trigger API."""
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.orm import Session

from ..config import load_config
from ..deps import get_db
from ..models import NewsSource
from ..schemas.common import ApiResponse
from ..schemas.trigger import TriggerFetchResponse
from ..tasks.fetch_task import fetch_all_sources
from ..utils.logger import logger

router = APIRouter(prefix="/api/v2/trigger", tags=["trigger"])

config = load_config()


def fetch_all_sources_sync(db, source_ids=None):
    import asyncio
    return asyncio.run(fetch_all_sources(db, config, source_ids=source_ids, sleep_between=True))


@router.post("/fetch")
async def trigger_fetch(
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,  # type: ignore[assignment]
    source_id: int | None = None,
    sync: bool = Query(False, description="Return immediately and run in background"),
):
    """Trigger a fetch run. By default fires-and-forgets (background).
    Use ?sync=true to wait for result.
    """
    ids = [source_id] if source_id else None
    if sync:
        results = fetch_all_sources_sync(db, source_ids=ids)
        return ApiResponse.success(TriggerFetchResponse(
            source="all" if ids is None else ids[0],
            status="completed",
            results=results,
        ).model_dump())

    background_tasks.add_task(fetch_all_sources_sync, db, ids)
    return ApiResponse.success({
        "source": "all" if ids is None else ids[0],
        "status": "triggered",
        "message": "Fetch started in background",
    })


@router.post("/fetch/source/{source_id}")
async def trigger_fetch_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(NewsSource).filter_by(id=source_id).first()
    if not source:
        return ApiResponse.error(404, "Source not found")
    results = fetch_all_sources_sync(db, source_ids=[source_id])
    return ApiResponse.success({
        "source": source.code,
        "status": "completed",
        "results": results,
    })