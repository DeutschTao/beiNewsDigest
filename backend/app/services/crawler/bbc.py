"""BBC News homepage crawler."""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from .base import BaseCrawler, CrawlResult, CrawledItem, parse_relative_time, get_logger

logger = get_logger("crawler.bbc")


class BBCCrawler(BaseCrawler):
    extra_headers = {
        "Referer": "https://www.google.com/",
    }

    # BBC Next.js 版的 URL 过滤：保留文章和体育内容
    URL_FILTERS = (
        re.compile(r"/news/articles/"),
        re.compile(r"/sport/"),
    )

    SKIP_KEYWORDS = ("video", "/videos/", "/live/", "/podcasts/", "/sounds/", "iplayer")

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

            # BBC 已迁移到 Next.js 架构，不再使用 <article> 或 data-testid='card'
            # 新的 DOM 结构使用 IndexCard（CSS Module hash class）作为新闻卡片容器
            for art in soup.select("[class*='IndexCard'], [class*='GridItem']"):
                a = art if art.name == "a" else art.select_one("a[href]")
                if not a or not a.get("href"):
                    continue
                href = a["href"]
                if not href.startswith("http"):
                    href = urljoin(self.config.homepage, href)
                if not any(p.search(href) for p in self.URL_FILTERS):
                    continue
                if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                title_el = art.select_one("h1, h2, h3, [data-testid='card-title']")
                title = (title_el.get_text(strip=True) if title_el else "").strip()
                if not title or len(title) < 10:
                    continue

                summary_el = art.select_one("p, [data-testid='card-description']")
                summary = (summary_el.get_text(strip=True) if summary_el else "")[:600]

                # BBC IndexCard 内有 <span> 包含相对时间如 "3 hrs ago"
                time_el = art.select_one("[class*='MetadataStyled'] span, [class*='MetadataStyled'] time")
                published_at = parse_relative_time(time_el.get_text(strip=True)) if time_el else None

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
                    published_at=published_at,
                    position=pos,
                ))
                if len(items) >= 50:
                    break

            result.items = items
            logger.info(f"BBC fetched {len(items)} items")
        except Exception as e:
            result.error = f"BBC fetch failed: {e}"
            logger.warning(result.error)
        return result
