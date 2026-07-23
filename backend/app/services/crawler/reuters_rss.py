"""Reuters via Google News RSS - fallback for direct Reuters feed (404)."""
from __future__ import annotations

from bs4 import BeautifulSoup
import feedparser

from .base import BaseCrawler, CrawlResult, CrawledItem, get_logger, parse_iso_date

logger = get_logger("crawler.reuters")


class ReutersViaGoogleNewsRSS(BaseCrawler):
    extra_headers = {
        "Referer": "https://news.google.com/",
    }

    URL_FILTER = "reuters.com"

    async def fetch_list(self) -> CrawlResult:
        result = CrawlResult(source_code=self.config.code)
        if not self.config.rss_url:
            result.error = "no rss_url"
            return result

        try:
            async with self._new_client() as client:
                resp = await client.get(self.config.rss_url)
                resp.raise_for_status()
                text = resp.text

            feed = feedparser.parse(text)
            if feed.bozo and not feed.entries:
                result.error = f"RSS parse error: {feed.bozo_exception}"
                return result

            pos = 0
            for entry in feed.entries:
                link = entry.get("link", "")
                if self.URL_FILTER not in link:
                    continue
                title = entry.get("title", "").strip()
                if not title:
                    continue

                # summary lives in 'summary' or 'description'
                raw_summary = entry.get("summary", "") or entry.get("description", "")
                summary_html = raw_summary
                summary = BeautifulSoup(summary_html, "lxml").get_text(" ").strip()
                summary = " ".join(summary.split())[:600]

                cover = None
                # Try media:content or media_thumbnail
                if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
                    cover = entry.media_thumbnail[0].get("url")
                if not cover and hasattr(entry, "media_content") and entry.media_content:
                    cover = entry.media_content[0].get("url")

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

            logger.info(f"Reuters (via GN RSS) fetched {len(result.items)} items")
        except Exception as e:
            result.error = f"Reuters RSS failed: {e}"
            logger.warning(result.error)
        return result