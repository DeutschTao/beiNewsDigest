"""AP News (World) homepage crawler."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, get_logger

logger = get_logger("crawler.ap")


class APCrawler(BaseCrawler):
    extra_headers = {
        "Referer": "https://www.google.com/",
    }

    URL_FILTERS = (re.compile(r"apnews\.com"),)
    SKIP_KEYWORDS = ("/video/", "/videos/", "/live/", "/hub/", "/photo", "/gallery")

    async def fetch_list(self) -> CrawlResult:
        result = CrawlResult(source_code=self.config.code)
        if not self.config.homepage:
            result.error = "no homepage"
            return result

        try:
            async with self._new_client() as client:
                resp = await client.get(self.config.homepage)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

            seen_urls = set()
            items: List[CrawledItem] = []
            pos = 0

            # AP News uses PageList / Card / bsp-card
            for art in soup.select("article, [class*='Card'], [class*='PageList']"):
                a = art if art.name == "a" else art.select_one("a[href]")
                if not a or not a.get("href"):
                    continue
                href = a["href"]
                if href.startswith("/"):
                    href = urljoin(self.config.homepage, href)
                if not any(p.search(href) for p in self.URL_FILTERS):
                    continue
                if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # AP paths look like /article/... or /article/<uuid>/<slug>
                if "/article/" not in href and not re.search(r"/[a-f0-9]{20,}", href):
                    continue

                title_el = art.select_one("h1, h2, h3, [class*='headline'], [class*='title']")
                title = (title_el.get_text(strip=True) if title_el else "").strip()
                if not title or len(title) < 10:
                    continue

                summary_el = art.select_one("p, [class*='description'], [class*='dek']")
                summary = (summary_el.get_text(strip=True) if summary_el else "")[:600]

                img_el = art.select_one("img")
                cover = None
                if img_el:
                    cover = img_el.get("src") or img_el.get("data-src")
                    if cover and cover.startswith("/"):
                        cover = urljoin(self.config.homepage, cover)

                pos += 1
                items.append(CrawledItem(
                    url=href,
                    title=title,
                    summary=summary,
                    cover_image=cover,
                    position=pos,
                ))
                if len(items) >= 50:
                    break

            result.items = items
            logger.info(f"AP fetched {len(items)} items")
        except Exception as e:
            result.error = f"AP fetch failed: {e}"
            logger.warning(result.error)
        return result