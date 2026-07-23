"""Offline integration test for fetch_task: crawler -> news_articles table."""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use a temp DB so we don't pollute the real one
TEST_DB_DIR = tempfile.mkdtemp(prefix="bei_news_test_")
os.environ["BEI_NEWS_CONFIG"] = ""  # ignore real config

from app.config import load_config, AppConfig
from app.database import Base, get_engine, get_session_factory
from app.models import NewsSource, NewsArticle
from app.services.rss_adapter import RSSAdapter
from app.services.crawler.base import SourceConfig


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test</title>
<item>
    <title>Article One</title>
    <link>https://example.com/1</link>
    <description>Summary 1</description>
    <pubDate>Mon, 21 Jul 2026 06:00:00 GMT</pubDate>
</item>
<item>
    <title>Article Two</title>
    <link>https://example.com/2</link>
    <description>Summary 2</description>
    <pubDate>Mon, 21 Jul 2026 07:00:00 GMT</pubDate>
</item>
<item>
    <title>Article Three (will be too old)</title>
    <link>https://example.com/3</link>
    <description>Old summary</description>
    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
</item>
</channel>
</rss>"""


class FakeClient:
    def __init__(self, *args, **kwargs): pass
    async def __aenter__(self): return self
    async def __aexit__(self, *args): return False
    async def get(self, url):
        class R:
            text = RSS_XML
            def raise_for_status(self): pass
        return R()


async def main():
    # 1. Init fresh test DB
    cfg = AppConfig()
    cfg.database.url = f"sqlite:///{TEST_DB_DIR}/test.db"
    engine = get_engine(cfg)
    SF = get_session_factory(engine)
    Base.metadata.create_all(engine)

    session = SF()
    src = NewsSource(
        code="test",
        name="Test Source",
        source_type="rss",
        rss_url="https://example.com/feed.xml",
        is_enabled=1,
        is_recommended=1,
        display_order=1,
        crawler_class="RSSAdapter",
    )
    session.add(src)
    session.commit()
    session.refresh(src)
    source_id = src.id
    print(f"Created test source id={source_id}")

    # 2. Monkey-patch the dispatcher
    from app.services import source_dispatcher

    class PatchedAdapter(RSSAdapter):
        def __init__(self, source_config):
            super().__init__(source_config)
            self._new_client = FakeClient

    source_dispatcher._CRAWLER_REGISTRY["RSSAdapter"] = PatchedAdapter

    # 3. Run fetch_all_sources (subset: just this one)
    from app.tasks.fetch_task import fetch_all_sources

    results = await fetch_all_sources(session, cfg, source_ids=[source_id], sleep_between=False)

    # 4. Verify
    print(f"Fetch results: {results}")
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["inserted"] == 2, f"Expected 2 inserted (3rd should be skipped as old), got {results[0]['inserted']}"

    articles = session.query(NewsArticle).order_by(NewsArticle.position).all()
    assert len(articles) == 2
    assert articles[0].title == "Article One"
    assert articles[0].position == 1
    assert articles[1].title == "Article Two"
    print(f"Articles in DB: {len(articles)} ✓")
    print(f"  - pos=1: {articles[0].title}, url_hash={articles[0].url_hash[:16]}")
    print(f"  - pos=2: {articles[1].title}, url_hash={articles[1].url_hash[:16]}")

    # 5. Re-run fetch -> should hit min_source_interval (intentional)
    # To test idempotency we directly call _fetch_one_source after overriding min_source_interval
    cfg.fetch.min_source_interval = 0
    results2 = await fetch_all_sources(session, cfg, source_ids=[source_id], sleep_between=False)
    print(f"Second fetch: {results2}")
    assert results2[0]["inserted"] == 0, f"Should insert 0 on rerun, got {results2[0].get('inserted')}"
    assert results2[0]["skipped"] >= 2, f"Should skip at least 2, got {results2[0].get('skipped')}"

    articles_after = session.query(NewsArticle).count()
    assert articles_after == 2, f"Expected still 2 articles, got {articles_after}"
    print(f"Idempotency: still {articles_after} articles ✓")

    session.close()

    # Cleanup
    shutil.rmtree(TEST_DB_DIR, ignore_errors=True)
    print()
    print("fetch_task offline integration test passed ✓")


if __name__ == "__main__":
    asyncio.run(main())