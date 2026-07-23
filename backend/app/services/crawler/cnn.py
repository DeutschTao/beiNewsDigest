"""CNN World homepage crawler."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, parse_relative_time, get_logger

logger = get_logger("crawler.cnn")

# CNN 页面中常见的噪音标题模式（图片来源署名等）
_TITLE_NOISE_PATTERNS = re.compile(
    r"(Getty Images|AFP|AFP/Getty|Reuters|AP Photo|EPA|EFE|"
    r"Press Service|Handout|Pool Photo|Anadolu|"
    r"Live Updates?\s*|•\s*Live Updates?)",
    re.IGNORECASE,
)


class CNNCrawler(BaseCrawler):
    extra_headers = {
        "Referer": "https://www.google.com/",
    }

    URL_FILTERS = (re.compile(r"\.cnn\.com"),)
    SKIP_KEYWORDS = ("/videos/", "/video/", "/live/", "/audio/", "/newsletters", "/account")

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

            # CNN 已移除 <article> 标签，改用 headless CMS 的 card 容器
            for art in soup.select("[class*='card']"):
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

                title_el = art.select_one("h1, h2, h3, [class*='headline'], [class*='title']")
                title = (title_el.get_text(strip=True) if title_el else "").strip()
                # 过滤噪音标题：太短或包含图片来源署名
                if not title or len(title) < 10:
                    continue
                if _TITLE_NOISE_PATTERNS.search(title) and len(title) < 30:
                    continue

                summary_el = art.select_one("p, [class*='description']")
                summary = (summary_el.get_text(strip=True) if summary_el else "")[:600]

                # CNN card 内的时间如 "29 min ago" 在 timestamp class 元素中
                time_el = art.select_one("[class*='timestamp']")
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
            logger.info(f"CNN fetched {len(items)} items")
        except Exception as e:
            result.error = f"CNN fetch failed: {e}"
            logger.warning(result.error)
        return result
