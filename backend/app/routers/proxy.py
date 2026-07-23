"""Image proxy and stats."""
from fastapi import APIRouter, Query
from fastapi.responses import Response
import httpx

from ..config import load_config
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/v2", tags=["misc"])
config = load_config()

_proxy = config.fetch.proxy if config.fetch.proxy_enabled else None


@router.get("/proxy/image")
async def proxy_image(url: str = Query(...)):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://www.bbc.com/",
        "Accept": "image/webp,image/avif,image/*,*/*;q=0.8",
    }
    kwargs = {"timeout": 15.0, "follow_redirects": True}
    if _proxy:
        kwargs["proxy"] = _proxy
    try:
        async with httpx.AsyncClient(**kwargs) as client:
            resp = await client.get(url, headers=headers)
        content_type = resp.headers.get("content-type", "image/jpeg")
        return Response(content=resp.content, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"})
    except Exception as e:
        return Response(content=b"", status_code=502)


@router.get("/stats")
def stats():
    from app.database import get_engine, get_session_factory
    from app.models import NewsSource, NewsArticle
    engine = get_engine(config)
    SF = get_session_factory(engine)
    db = SF()
    try:
        total_sources = db.query(NewsSource).count()
        enabled_sources = db.query(NewsSource).filter_by(is_enabled=1).count()
        total_articles = db.query(NewsArticle).count()
        return ApiResponse.success({
            "total_sources": total_sources,
            "enabled_sources": enabled_sources,
            "total_articles": total_articles,
        })
    finally:
        db.close()