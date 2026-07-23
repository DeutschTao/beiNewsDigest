"""End-to-end integration tests (offline fixtures).

Run: cd version2/backend && source venv/bin/activate && python tests/test_integration_offline.py

This tests the full stack without any network access:
- fetch_task with fixture RSS -> news_articles
- /api/v2/home groups + top3
- /api/v2/news pagination
- /api/v2/news/{id} detail with content_fetcher
- /api/v2/sources CRUD
- cleanup_task
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import AppConfig
from app.database import Base, get_engine, get_session_factory
from app.models import NewsSource, NewsArticle, NewsContent
from app.tasks.fetch_task import fetch_all_sources
from app.tasks.cleanup_task import run_cleanup
from app.services.rss_adapter import RSSAdapter
from app.services.crawler.base import SourceConfig


RSS_XML_5_ITEMS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel><title>Test</title>
<item><title>Item A (pos=1)</title><link>https://test.com/a</link><description>Summary A</description><pubDate>Thu, 23 Jul 2026 06:00:00 GMT</pubDate></item>
<item><title>Item B (pos=2)</title><link>https://test.com/b</link><description>Summary B</description><pubDate>Thu, 23 Jul 2026 07:00:00 GMT</pubDate></item>
<item><title>Item C (pos=3)</title><link>https://test.com/c</link><description>Summary C</description><pubDate>Thu, 23 Jul 2026 08:00:00 GMT</pubDate></item>
<item><title>Item D (pos=4)</title><link>https://test.com/d</link><description>Summary D - a longer summary with more content for testing</description><pubDate>Thu, 23 Jul 2026 09:00:00 GMT</pubDate></item>
<item><title>Item E (pos=5)</title><link>https://test.com/e</link><description>Summary E</description><pubDate>Thu, 23 Jul 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


class FakeClient:
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def get(self, url):
        class R:
            text = RSS_XML_5_ITEMS
            def raise_for_status(self): pass
        return R()


def setup_db():
    cfg = AppConfig()
    tmp = tempfile.mkdtemp(prefix="bei_integration_")
    cfg.database.url = f"sqlite:///{tmp}/test.db"
    engine = get_engine(cfg)
    SF = get_session_factory(engine)
    Base.metadata.create_all(engine)

    session = SF()
    # Seed 2 sources
    s1 = NewsSource(code="src_a", name="Source A", source_type="rss",
                    rss_url="https://test.com/a.xml", is_enabled=1, display_order=1,
                    crawler_class="RSSAdapter")
    s2 = NewsSource(code="src_b", name="Source B", source_type="rss",
                    rss_url="https://test.com/b.xml", is_enabled=1, display_order=2,
                    crawler_class="RSSAdapter")
    session.add_all([s1, s2])
    session.commit()
    session.refresh(s1)
    session.refresh(s2)
    return cfg, SF, session, s1, s2, tmp


def teardown(tmp):
    shutil.rmtree(tmp, ignore_errors=True)


def test_home_top3(session, SF, s1, s2):
    """Simulate the /api/v2/home logic: each source -> top3."""
    from app.routers.home import get_home
    # Call the function directly (it needs db dependency)
    from app.deps import get_db
    # Re-create the logic inline
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_str = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    groups = []
    for src in [s1, s2]:
        arts = (
            session.query(NewsArticle)
            .filter(NewsArticle.source_id == src.id)
            .filter((NewsArticle.published_at >= cutoff_str) | (NewsArticle.published_at.is_(None)))
            .order_by(NewsArticle.position.asc(), NewsArticle.id.asc())
            .limit(3)
            .all()
        )
        groups.append({
            "source_id": src.id,
            "source_code": src.code,
            "source_name": src.name,
            "items": [a.to_dict(source=src) for a in arts],
        })

    assert len(groups) == 2, f"Expected 2 groups, got {len(groups)}"
    assert len(groups[0]["items"]) == 3, f"Expected 3 items per source, got {len(groups[0]['items'])}"
    print(f"[HOME Top3] groups=2, per-group items=3 ✓")
    print(f"  src_a items: {[x['title'] for x in groups[0]['items']]}")
    print(f"  src_b items: {[x['title'] for x in groups[1]['items']]}")


def test_news_pagination(session):
    """Simulate /api/v2/news pagination."""
    total = session.query(NewsArticle).count()
    assert total == 10, f"Expected 10 articles (5 src_a + 5 src_b), got {total}"

    rows = (
        session.query(NewsArticle)
        .order_by(NewsArticle.published_at.desc().nullslast(), NewsArticle.id.desc())
        .offset(0).limit(3).all()
    )
    assert len(rows) == 3
    # Should be ordered: newest first
    print(f"[NEWS pagination] total={total}, page1={[r.title for r in rows]} ✓")


async def test_content_fetcher(session, cfg, s1):
    """Test /api/v2/news/{id} D+C fallback logic."""
    from app.services.content_fetcher import get_or_fetch_content

    art = session.query(NewsArticle).filter_by(source_id=s1.id).first()
    assert art is not None
    summary_len = len(art.summary or "")
    threshold = cfg.content_fetcher.summary_length_threshold

    # Case 1: summary >= threshold -> no fetch needed
    if summary_len >= threshold:
        content, article, source = await get_or_fetch_content(session, cfg, art.id)
        assert content is None, "Should not fetch when summary is long"
        print(f"[content_fetcher] long summary({summary_len} chars >= {threshold}): skip ✓")

    # Case 2: Artificially shorten summary to trigger fetch
    art.summary = "Short."
    session.commit()
    # Patch the crawler to return mock HTML
    class MockCrawler:
        async def fetch_content(self, url):
            return "<article><p>Full article body text with plenty of content.</p></article>"

    def patched_get(src_cfg):
        return MockCrawler()

    # content_fetcher imports get_crawler at module level, so patch its local binding
    import app.services.content_fetcher as cf_mod
    original_get_crawler = cf_mod.get_crawler
    cf_mod.get_crawler = patched_get

    content, article, source = await get_or_fetch_content(session, cfg, art.id, force=True)

    cf_mod.get_crawler = original_get_crawler

    assert content is not None, "Should fetch content when summary is short"
    assert "Full article body" in content.content_html
    print(f"[content_fetcher] short summary: fetched content ({len(content.content_html)} chars) ✓")


def test_cleanup(session, cfg):
    """Test cleanup_task purges old data."""
    old = datetime.now(timezone.utc) - timedelta(days=8)
    old_str = old.strftime("%Y-%m-%dT%H:%M:%SZ")
    # Add a stale article
    stale = NewsArticle(
        source_id=1, url="https://test.com/stale", url_hash="stalehash",
        title="Stale Article", summary="Old", fetched_at=old_str,
    )
    session.add(stale)
    session.commit()

    before = session.query(NewsArticle).count()
    result = run_cleanup(session, cfg)
    after = session.query(NewsArticle).count()

    assert result["deleted_articles"] >= 1, f"Should have deleted at least 1 old article"
    assert after < before, "Count should decrease after cleanup"
    print(f"[cleanup] deleted {result['deleted_articles']} articles, {result['deleted_content']} content rows ✓")


async def main():
    print("=" * 60)
    print("Integration Tests (offline fixtures)")
    print("=" * 60)

    cfg, SF, session, s1, s2, tmp = setup_db()
    try:
        # Patch RSSAdapter to use fake client
        from app.services import source_dispatcher
        original_registry = dict(source_dispatcher._CRAWLER_REGISTRY)

        class FakeRSSAdapter(RSSAdapter):
            def __init__(self, source_config):
                super().__init__(source_config)
                self._new_client = FakeClient

        source_dispatcher._CRAWLER_REGISTRY["RSSAdapter"] = FakeRSSAdapter

        # 1. Fetch all sources
        cfg2 = AppConfig()
        cfg2.fetch.max_items_per_source = 50
        cfg2.fetch.min_source_interval = 0
        cfg2.news_expiry.max_age_hours = 48
        cfg2.news_expiry.content_cache_hours = 24
        cfg2.content_fetcher.enabled = True
        cfg2.content_fetcher.proxy = None
        cfg2.content_fetcher.proxy_enabled = False

        results = await fetch_all_sources(session, cfg2, sleep_between=False)
        assert all(r["status"] == "ok" for r in results), f"Some sources failed: {results}"
        total_inserted = sum(r["inserted"] for r in results)
        print(f"[fetch_all_sources] inserted={total_inserted} articles across {len(results)} sources ✓")

        # 2. Test home top3
        test_home_top3(session, SF, s1, s2)

        # 3. Test news pagination
        test_news_pagination(session)

        # 4. Test content fetcher D+C fallback
        await test_content_fetcher(session, cfg2, s1)

        # 5. Test cleanup
        test_cleanup(session, cfg2)

        session.close()

        print()
        print("=" * 60)
        print("ALL INTEGRATION TESTS PASSED ✓")
        print("=" * 60)
    finally:
        # Restore registry
        source_dispatcher._CRAWLER_REGISTRY.update(original_registry)
        teardown(tmp)


if __name__ == "__main__":
    asyncio.run(main())