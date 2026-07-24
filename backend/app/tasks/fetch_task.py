"""Fetch task - iterate sources, run their crawler, upsert into news_articles."""
from __future__ import annotations

import asyncio
import hashlib
import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..config import AppConfig
from ..models import NewsArticle, NewsSource
from ..models.news_article import compute_sort_at
from ..services.source_dispatcher import get_crawler
from ..services.crawler.base import SourceConfig
from ..utils.logger import logger


def _url_hash(source_code: str, url: str) -> str:
    return hashlib.sha1(f"{source_code}|{url}".encode("utf-8")).hexdigest()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _fetch_one_source(
    db: Session,
    config: AppConfig,
    source: NewsSource,
    max_items: int,
) -> dict:
    """Run the crawler for a single source. Returns a stats dict."""
    src_cfg = SourceConfig.from_db(
        source,
        proxy=config.fetch.proxy,
        proxy_enabled=config.fetch.proxy_enabled,
        timeout=config.fetch.timeout,
    )
    crawler = get_crawler(src_cfg)
    try:
        result = await crawler.fetch_list()
    except Exception as e:
        logger.warning(f"fetch error for {source.code}: {e}")
        return {"source": source.code, "status": "error", "message": str(e), "fetched": 0, "inserted": 0, "skipped": 0}

    if result.error:
        logger.warning(f"{source.code} fetch error: {result.error}")
        return {"source": source.code, "status": "error", "message": result.error, "fetched": 0, "inserted": 0, "skipped": 0}

    cutoff = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=config.news_expiry.max_age_hours)
    inserted = 0
    skipped = 0
    seen_hashes: set[str] = set()

    for item in result.items[:max_items]:
        if not item.url or not item.title:
            skipped += 1
            continue

        # Age filter (only if published_at can be parsed)
        if item.published_at:
            ts = _parse_iso(item.published_at)
            if ts and ts < cutoff:
                skipped += 1
                continue

        uhash = _url_hash(source.code, item.url)
        if uhash in seen_hashes:
            skipped += 1
            continue
        seen_hashes.add(uhash)

        fetched_at = _now()
        sort_at = compute_sort_at(item.published_at, fetched_at)

        # Upsert (idempotent on url_hash)
        existing = db.query(NewsArticle).filter_by(url_hash=uhash).first()
        if existing:
            # Update mutable fields but keep position stable
            existing.title = item.title or existing.title
            existing.summary = item.summary or existing.summary
            existing.cover_image = item.cover_image or existing.cover_image
            existing.author = item.author or existing.author
            existing.published_at = item.published_at or existing.published_at
            existing.sort_at = compute_sort_at(existing.published_at, existing.fetched_at)
            skipped += 1
            continue

        db.add(NewsArticle(
            source_id=source.id,
            url=item.url,
            url_hash=uhash,
            title=item.title[:500],
            summary=item.summary[:2000] if item.summary else None,
            cover_image=item.cover_image,
            author=item.author,
            published_at=item.published_at,
            fetched_at=fetched_at,
            sort_at=sort_at,
            position=item.position,
        ))
        inserted += 1

    db.commit()
    return {
        "source": source.code,
        "status": "ok",
        "fetched": len(result.items),
        "inserted": inserted,
        "skipped": skipped,
    }


async def fetch_all_sources(
    db: Session,
    config: AppConfig,
    source_ids: list[int] | None = None,
    sleep_between: bool = True,
) -> list[dict]:
    """Fetch all enabled sources. Returns per-source stats."""
    q = db.query(NewsSource).filter(NewsSource.is_enabled == 1)
    if source_ids:
        q = q.filter(NewsSource.id.in_(source_ids))
    sources = q.order_by(NewsSource.display_order).all()

    results: list[dict] = []
    for idx, src in enumerate(sources):
        # Skip if recently fetched
        last_article = db.query(NewsArticle).filter_by(source_id=src.id).order_by(NewsArticle.fetched_at.desc()).first()
        if last_article and last_article.fetched_at:
            from datetime import datetime as _dt
            try:
                last_ts = _dt.fromisoformat(last_article.fetched_at.replace("Z", "+00:00"))
                if last_ts.tzinfo is None:
                    last_ts = last_ts.replace(tzinfo=timezone.utc)
                elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds()
                if elapsed < config.fetch.min_source_interval:
                    logger.info(f"Skipping {src.code}: last fetched {int(elapsed)}s ago (min {config.fetch.min_source_interval}s)")
                    results.append({"source": src.code, "status": "skipped", "message": "min_source_interval"})
                    continue
            except Exception:
                pass

        stat = await _fetch_one_source(db, config, src, config.fetch.max_items_per_source)
        results.append(stat)
        logger.info(f"fetch[{src.code}]: {stat}")

        if sleep_between and idx < len(sources) - 1:
            lo, hi = config.fetch.rate_limit_seconds
            await asyncio.sleep(random.uniform(lo, hi))

    return results


def fetch_all_sources_sync(
    db: Session,
    config: AppConfig,
    source_ids: list[int] | None = None,
) -> list[dict]:
    return asyncio.run(fetch_all_sources(db, config, source_ids))