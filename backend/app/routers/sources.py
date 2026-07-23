"""News source management API."""
import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..config import load_config
from ..deps import get_db
from ..models import NewsArticle, NewsSource
from ..schemas.common import ApiResponse
from ..schemas.news_source import AddSourceRequest
from ..services.rss_adapter import RSSAdapter
from ..services.crawler.generic_html import GenericHTMLCrawler
from ..services.crawler.base import SourceConfig
from ..utils.exceptions import NotFoundError, RSSParseError, SourceExistsError, SourceLimitError
from ..utils.logger import logger

router = APIRouter(prefix="/api/v2/sources", tags=["sources"])

config = load_config()


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    presets = (
        db.query(NewsSource)
        .filter(NewsSource.is_recommended == 1)
        .order_by(NewsSource.display_order)
        .all()
    )
    custom = (
        db.query(NewsSource)
        .filter(NewsSource.is_recommended == 0)
        .order_by(NewsSource.display_order, NewsSource.id)
        .all()
    )
    return ApiResponse.success({
        "preset_sources": [s.to_dict() for s in presets],
        "custom_sources": [s.to_dict() for s in custom],
    })


@router.post("/custom")
async def add_custom_source(req: AddSourceRequest, db: Session = Depends(get_db)):
    existing = (
        db.query(NewsSource)
        .filter(NewsSource.rss_url == req.url if req.source_type == "rss" else NewsSource.homepage_url == req.url)
        .first()
    )
    if existing:
        raise SourceExistsError("This URL has already been added")

    total = db.query(NewsSource).count()
    if total >= config.api.max_sources:
        raise SourceLimitError()

    if req.source_type == "rss":
        # Validate by fetching one item
        cfg = SourceConfig(
            code="validate", name="validate", type="rss",
            rss_url=req.url, proxy=config.fetch.proxy,
            proxy_enabled=config.fetch.proxy_enabled,
            timeout=config.api.custom_source_validate_timeout,
        )
        adapter = RSSAdapter(cfg)
        result = await adapter.fetch_list()
        if result.error or not result.items:
            raise RSSParseError("Invalid or unreachable RSS URL. Please check the link and try again.")
    else:
        cfg = SourceConfig(
            code="validate", name="validate", type="crawler",
            homepage=req.url, proxy=config.fetch.proxy,
            proxy_enabled=config.fetch.proxy_enabled,
            timeout=config.api.custom_source_validate_timeout,
        )
        crawler = GenericHTMLCrawler(cfg)
        result = await crawler.fetch_list()
        if result.error or not result.items:
            raise RSSParseError("Invalid or unreachable URL. Please check the link and try again.")

    # Derive name & code
    name = (req.name or "").strip()
    if not name:
        first = result.items[0]
        name = first.title[:50] if first.title else "Custom Source"

    code_base = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())[:20]
    code = f"custom_{code_base}" if code_base else "custom_src"
    counter = 1
    while db.query(NewsSource).filter(NewsSource.code == code).first():
        code = f"custom_{code_base}_{counter}" if code_base else f"custom_src_{counter}"
        counter += 1

    source = NewsSource(
        code=code,
        name=name,
        source_type=req.source_type,
        homepage_url=req.url if req.source_type == "crawler" else None,
        rss_url=req.url if req.source_type == "rss" else None,
        category="general",
        crawler_class="RSSAdapter" if req.source_type == "rss" else "GenericHTMLCrawler",
        is_enabled=1,
        is_recommended=0,
        display_order=999,
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    logger.info(f"Added custom source: {source.name} (code={source.code}, type={source.source_type})")
    return ApiResponse.success(source.to_dict())


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise NotFoundError("News source not found")
    if source.is_recommended:
        # preset sources can be toggled, not deleted
        return ApiResponse.error(400, "Preset sources cannot be deleted. Toggle them instead.")

    db.query(NewsArticle).filter(NewsArticle.source_id == source_id).delete()
    db.delete(source)
    db.commit()
    logger.info(f"Deleted source: {source.name} (id={source_id})")
    return ApiResponse.success()


@router.patch("/{source_id}/toggle")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise NotFoundError("News source not found")
    source.is_enabled = 0 if source.is_enabled else 1
    db.commit()
    logger.info(f"Toggled {source.name}: enabled={source.is_enabled}")
    return ApiResponse.success({
        "id": source.id,
        "is_enabled": bool(source.is_enabled),
    })


@router.post("/check/{source_id}")
async def check_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(NewsSource).filter(NewsSource.id == source_id).first()
    if not source:
        raise NotFoundError("News source not found")

    cfg = SourceConfig(
        code=source.code, name=source.name, type=source.source_type,
        homepage=source.homepage_url, rss_url=source.rss_url,
        crawler_class=source.crawler_class,
        proxy=config.fetch.proxy, proxy_enabled=config.fetch.proxy_enabled,
        timeout=config.api.custom_source_validate_timeout,
    )
    if source.source_type == "rss":
        adapter = RSSAdapter(cfg)
        result = await adapter.fetch_list()
    else:
        from ..services.source_dispatcher import get_crawler
        crawler = get_crawler(cfg)
        result = await crawler.fetch_list()

    status = "error" if result.error else "ok"
    msg = result.error or f"OK ({len(result.items)} items)"
    return ApiResponse.success({
        "id": source.id,
        "name": source.name,
        "code": source.code,
        "status": status,
        "message": msg,
    })