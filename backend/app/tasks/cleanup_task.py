"""Cleanup task - purge old articles and expired content cache."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..config import AppConfig
from ..models import NewsArticle, NewsContent
from ..utils.logger import get_logger

logger = get_logger("cleanup")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cleanup(db: Session, config: AppConfig) -> dict:
    """Delete articles older than retention_days and expired content cache entries."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.news_expiry.retention_days)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Delete old articles
    result = db.query(NewsArticle).filter(NewsArticle.fetched_at < cutoff_str)
    deleted_articles = result.delete(synchronize_session=False)

    # Delete expired content cache
    expired = db.query(NewsContent).filter(NewsContent.expires_at < _now())
    deleted_content = expired.delete(synchronize_session=False)

    db.commit()
    logger.info(f"Cleanup done: {deleted_articles} articles, {deleted_content} content rows purged")
    return {"deleted_articles": deleted_articles, "deleted_content": deleted_content}