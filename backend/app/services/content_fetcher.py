"""On-demand detail-page fetcher with caching."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .source_dispatcher import get_crawler
from ..config import AppConfig
from ..models import NewsArticle, NewsContent, NewsSource
from ..services.crawler.base import SourceConfig
from ..utils.logger import get_logger

logger = get_logger("content_fetcher")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def get_or_fetch_content(
    db: Session,
    config: AppConfig,
    article_id: int,
    force: bool = False,
) -> tuple[Optional[NewsContent], Optional[NewsArticle], Optional[NewsSource]]:
    """
    Async function. Returns (content, article, source). If no cached content (or expired), fetches on demand.
    Returns (None, article, source) if no content is available.
    """
    article: NewsArticle | None = db.query(NewsArticle).filter_by(id=article_id).first()
    if not article:
        return None, None, None
    source: NewsSource | None = db.query(NewsSource).filter_by(id=article.source_id).first()
    if not source:
        return None, article, None

    # Cache hit?
    if not force:
        cached: NewsContent | None = db.query(NewsContent).filter_by(news_id=article.id).first()
        if cached and cached.expires_at > _now():
            return cached, article, source

    # Should we fetch on demand?
    if not config.content_fetcher.enabled:
        return None, article, source

    # Strategy: force_fetch = True → always fetch; False → only if summary is too short
    if not config.content_fetcher.force_fetch:
        threshold = config.content_fetcher.summary_length_threshold
        if (article.summary or "") and len(article.summary) >= threshold:
            return None, article, source

    src_cfg = SourceConfig.from_db(
        source,
        proxy=config.content_fetcher.proxy,
        proxy_enabled=config.content_fetcher.proxy_enabled,
        timeout=config.content_fetcher.timeout,
    )
    crawler = get_crawler(src_cfg)
    try:
        html = await crawler.fetch_content(article.url)
    except Exception as e:
        logger.warning(f"content fetch failed for article {article_id}: {e}")
        return None, article, source

    if not html:
        return None, article, source

    expires = (datetime.now(timezone.utc) + timedelta(hours=config.news_expiry.content_cache_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    content = NewsContent(
        news_id=article.id,
        content_html=html[:200_000],
        fetched_at=_now(),
        expires_at=expires,
    )
    db.merge(content)
    db.commit()
    logger.info(f"Cached full content for article {article_id}, expires at {expires}")
    return content, article, source