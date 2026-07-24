"""News API - list & detail."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import load_config
from ..deps import get_db
from ..models import NewsArticle, NewsContent, NewsSource
from ..schemas.common import ApiResponse
from ..services.content_fetcher import get_or_fetch_content
from ..utils.exceptions import NotFoundError
from ..utils.logger import logger

router = APIRouter(prefix="/api/v2/news", tags=["news"])

config = load_config()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@router.get("")
def list_news(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source_id: int | None = Query(None, description="Filter by source"),
):
    """Paginated list of all articles within the list_window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.news_expiry.list_window_hours)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    q = db.query(NewsArticle, NewsSource).join(NewsSource, NewsArticle.source_id == NewsSource.id)
    q = q.filter((NewsArticle.published_at >= cutoff_str) | (NewsArticle.published_at.is_(None)))
    if source_id:
        q = q.filter(NewsArticle.source_id == source_id)
    total = q.count()
    rows = (
        q.order_by(NewsArticle.sort_at.desc(), NewsArticle.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    items = []
    for art, src in rows:
        d = art.to_dict(source=src)
        d.pop("source_code", None)
        d["source_id"] = src.id
        d["source_code"] = src.code
        items.append(d)
    return ApiResponse.success({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{news_id}")
async def get_news_detail(news_id: int, db: Session = Depends(get_db)):
    """Return article + on-demand full content if available."""
    # On-demand content fetch (async; uses app.state session factory inside)
    content, article, source = await get_or_fetch_content(db, config, news_id)

    if not article:
        raise NotFoundError("News not found")
    if not source:
        raise NotFoundError("News source not found")

    has_full = bool(content and content.content_html)
    payload = {
        "id": article.id,
        "title": article.title,
        "summary": article.summary or "",
        "cover_image": article.cover_image,
        "url": article.url,
        "published_at": article.published_at,
        "source_id": source.id,
        "source_code": source.code,
        "source_name": source.name,
        "has_full_content": has_full,
        "content_html": content.content_html if content else None,
        "content_source": "fetched" if has_full else ("rss" if source.source_type == "rss" else "homepage"),
        "fetched_at": content.fetched_at if content else None,
    }
    return ApiResponse.success(payload)