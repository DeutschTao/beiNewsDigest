"""Home API - per-source Top3 by sort_at."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import load_config
from ..deps import get_db
from ..models import NewsArticle, NewsSource
from ..schemas.common import ApiResponse
from ..utils.logger import logger

router = APIRouter(prefix="/api/v2/home", tags=["home"])

config = load_config()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("")
def get_home(
    db: Session = Depends(get_db),
    limit: int = Query(3, ge=1, le=10),
):
    """Return enabled sources, each with up to `limit` items ordered by sort_at DESC."""
    enabled_sources = (
        db.query(NewsSource)
        .filter(NewsSource.is_enabled == 1)
        .order_by(NewsSource.display_order)
        .all()
    )

    groups = []
    for src in enabled_sources:
        articles = (
            db.query(NewsArticle)
            .filter(NewsArticle.source_id == src.id)
            .order_by(
                NewsArticle.sort_at.desc(),
                NewsArticle.position.asc(),
            )
            .limit(limit)
            .all()
        )

        if not articles:
            groups.append({
                "source_id": src.id,
                "source_code": src.code,
                "source_name": src.name,
                "items": [],
            })
            continue

        items = [a.to_dict(source=src) for a in articles]
        groups.append({
            "source_id": src.id,
            "source_code": src.code,
            "source_name": src.name,
            "items": items,
        })

    # Sort groups by their latest article's sort_at DESC
    def _group_latest_time(group):
        if not group["items"]:
            return datetime.min.replace(tzinfo=timezone.utc)
        ts_str = group["items"][0].get("sort_at") or "1970-01-01T00:00:00Z"
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    groups.sort(key=_group_latest_time, reverse=True)

    return ApiResponse.success({
        "groups": groups,
        "updated_at": _now(),
        "total_sources": len(groups),
    })
