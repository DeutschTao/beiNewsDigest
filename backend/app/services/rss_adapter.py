"""RSS adapter for user-added custom RSS sources (and Reuters fallback parity)."""
from __future__ import annotations

from typing import Optional

import feedparser
from bs4 import BeautifulSoup
import httpx

from .crawler.base import BaseCrawler, CrawlResult, CrawledItem, get_logger, parse_iso_date

logger = get_logger("crawler.rss_adapter")


class RSSAdapter(BaseCrawler):
    """For user-added custom RSS sources."""

    extra_headers: dict = {}

    def __init__(self, source_config: "SourceConfig"):
        super().__init__(source_config)
        # RSSAdapter always reads rss_url
        self.feed_url = source_config.rss_url

    async def fetch_list(self) -> CrawlResult:
        result = CrawlResult(source_code=self.config.code)
        if not self.feed_url:
            result.error = "no rss_url"
            return result

        try:
            async with self._new_client() as client:
                resp = await client.get(self.feed_url)
                resp.raise_for_status()
                text = resp.text

            feed = feedparser.parse(text)
            if feed.bozo and not feed.entries:
                result.error = f"RSS parse error: {feed.bozo_exception}"
                return result

            pos = 0
            for entry in feed.entries:
                link = entry.get("link", "").strip()
                title = entry.get("title", "").strip()
                if not link or not title:
                    continue

                raw_summary = entry.get("summary", "") or entry.get("description", "")
                summary = BeautifulSoup(raw_summary, "lxml").get_text(" ").strip()
                summary = " ".join(summary.split())[:600]

                cover = None
                if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    cover = entry.media_thumbnail[0].get("url")
                if not cover and hasattr(entry, "media_content") and entry.media_content:
                    cover = entry.media_content[0].get("url")
                if not cover and hasattr(entry, "enclosures") and entry.enclosures:
                    for enc in entry.enclosures:
                        if enc.get("type", "").startswith("image"):
                            cover = enc.get("href") or enc.get("url")
                            break

                pos += 1
                result.items.append(CrawledItem(
                    url=link,
                    title=title,
                    summary=summary,
                    cover_image=cover,
                    author=entry.get("author", "") or None,
                    published_at=parse_iso_date(entry.get("published") or entry.get("updated")),
                    position=pos,
                ))
                if len(result.items) >= 50:
                    break

            logger.info(f"RSSAdapter fetched {len(result.items)} items for {self.config.code}")
        except Exception as e:
            result.error = f"RSSAdapter fetch failed: {e}"
            logger.warning(result.error)
        return result

    async def fetch_content(self, url: str) -> Optional[str]:
        """RSS 源的详情 URL 可以直接抓取全文。

        尝试用父类方法抓取 HTML 并提取正文。
        """
        try:
            async with self._new_client() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return self._extract_content_html(resp.text)
        except Exception as e:
            logger.warning(f"RSSAdapter fetch_content failed for {url[:60]}: {e}")
            return None