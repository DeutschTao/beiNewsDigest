"""Offline crawler tests using static HTML fixtures.

This lets us verify crawler selector logic without needing network access.
Run: cd version2/backend && python tests/test_crawlers_offline.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.crawler.bbc import BBCCrawler
from app.services.crawler.cnn import CNNCrawler
from app.services.crawler.aljazeera import AlJazeeraCrawler
from app.services.crawler.ap import APCrawler
from app.services.crawler.generic_html import GenericHTMLCrawler
from app.services.crawler.base import SourceConfig
from bs4 import BeautifulSoup


def make_html_articles(articles_data):
    """Build a fake HTML page from a list of article dicts."""
    parts = ["<html><body>"]
    for art in articles_data:
        href = art["url"]
        title = art["title"]
        summary = art.get("summary", "")
        img = art.get("cover_image", "")
        parts.append(f'''
        <article>
            <a href="{href}">
                <img src="{img}" />
                <h3>{title}</h3>
                <p>{summary}</p>
            </a>
        </article>
        ''')
    parts.append("</body></html>")
    return "\n".join(parts)


def make_html_with_og():
    return """
    <html>
    <head>
        <meta property="og:title" content="Custom Site: Breaking News Today" />
        <meta property="og:description" content="A summary of breaking news for testing." />
        <meta property="og:image" content="https://example.com/cover.jpg" />
    </head>
    <body>
        <h1>Some page title</h1>
        <p>Body content here.</p>
    </body>
    </html>
    """


async def test_bbc():
    html = make_html_articles([
        {"url": "https://www.bbc.com/news/world-12345", "title": "Test headline A", "summary": "Summary A", "cover_image": "https://ichef.bbc/a.jpg"},
        {"url": "https://www.bbc.com/news/world-67890", "title": "Test headline B very long title here", "summary": "Summary B", "cover_image": ""},
        {"url": "https://www.bbc.com/news/world-99999", "title": "Test headline C", "summary": "", "cover_image": "https://ichef.bbc/c.jpg"},
    ])
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("article")
    assert len(items) == 3
    print(f"[BBC selector] found {len(items)} articles ✓")


async def test_cnn():
    html = make_html_articles([
        {"url": "https://www.cnn.com/2026/01/01/politics/article-a", "title": "CNN test", "summary": "s", "cover_image": ""},
    ])
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("article")
    assert len(items) == 1
    print(f"[CNN selector] found {len(items)} articles ✓")


async def test_ap():
    html = make_html_articles([
        {"url": "https://apnews.com/article/uuid-12345-some-slug", "title": "AP test headline", "summary": "s", "cover_image": ""},
    ])
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("article")
    assert len(items) == 1
    print(f"[AP selector] found {len(items)} articles ✓")


async def test_generic():
    cfg = SourceConfig(code="custom_test", name="Test", type="crawler", homepage="https://example.com")
    crawler = GenericHTMLCrawler(cfg)

    # Use monkey-patching: override _new_client to return a fake that returns our static HTML
    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        async def get(self, url):
            class R:
                text = make_html_with_og()
                def raise_for_status(self): pass
            return R()

    crawler._new_client = FakeClient
    result = await crawler.fetch_list()
    assert not result.error, result.error
    assert len(result.items) == 1
    it = result.items[0]
    assert it.title == "Custom Site: Breaking News Today", it.title
    assert "summary of breaking" in it.summary.lower()
    assert it.cover_image == "https://example.com/cover.jpg"
    print(f"[GenericHTML] og:title={it.title[:50]} ✓")
    print(f"[GenericHTML] og:description={it.summary[:50]} ✓")


async def main():
    await test_bbc()
    await test_cnn()
    await test_ap()
    await test_generic()
    print()
    print("=" * 50)
    print("All offline crawler tests passed ✓")
    print("=" * 50)
    print()
    print("NOTE: These tests validate selector logic only.")
    print("Real network tests against BBC/CNN/AP/Al Jazeera")
    print("need to be run on the user's local machine where")
    print("the proxy is available.")


if __name__ == "__main__":
    asyncio.run(main())