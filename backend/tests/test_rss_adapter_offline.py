"""Offline tests for RSSAdapter with a static RSS XML fixture."""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.rss_adapter import RSSAdapter
from app.services.crawler.base import SourceConfig


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Test Feed</title>
<link>https://example.com</link>
<description>Test</description>
<item>
    <title>Test Article 1</title>
    <link>https://example.com/news/1</link>
    <description>This is a summary of article 1.</description>
    <pubDate>Mon, 21 Jul 2026 06:00:00 GMT</pubDate>
    <author>Reporter A</author>
</item>
<item>
    <title>Test Article 2 with longer title</title>
    <link>https://example.com/news/2</link>
    <description>Summary 2 here.</description>
    <pubDate>Mon, 21 Jul 2026 07:30:00 GMT</pubDate>
</item>
<item>
    <title>Should be skipped (no link)</title>
    <description>no link</description>
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
    cfg = SourceConfig(code="test_rss", name="Test", type="rss", rss_url="https://example.com/feed.xml")
    crawler = RSSAdapter(cfg)
    crawler._new_client = FakeClient

    result = await crawler.fetch_list()
    assert not result.error, result.error
    assert len(result.items) == 2, f"Expected 2 items, got {len(result.items)}"

    item1 = result.items[0]
    assert item1.url == "https://example.com/news/1"
    assert item1.title == "Test Article 1"
    assert item1.summary == "This is a summary of article 1."
    assert item1.author == "Reporter A"
    assert item1.published_at is not None
    assert item1.position == 1

    item2 = result.items[1]
    assert item2.position == 2
    assert item2.author is None

    print(f"[RSSAdapter] parsed {len(result.items)} items from fixture RSS ✓")
    print(f"  item1: {item1.title}")
    print(f"  item1.published_at: {item1.published_at}")
    print(f"  item2.position: {item2.position}")
    print()
    print("RSSAdapter offline test passed ✓")


if __name__ == "__main__":
    asyncio.run(main())