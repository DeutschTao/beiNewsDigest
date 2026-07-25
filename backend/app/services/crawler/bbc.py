"""BBC News homepage crawler (bbc.com/news, bbc.co.uk/news).

适配 BBC Next.js 架构的 data-testid 选择器。
当前适配 bbc.com/news，bbc.co.uk/news 的 DOM 结构一致，
如需差异化行为可另建 BBCCoCrawlerUK 类。
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, parse_relative_time, get_logger

logger = get_logger("crawler.bbc")

# 两个板块的 data-testid（bbc.com / bbc.co.uk 共用）
_TOP_SECTION = "virginia-section-outer-8"
_SECOND_SECTION = "ohio-section-outer-5"


class BBCCrawler(BaseCrawler):
    """抓取 BBC 首页前两个板块：Virginia-8（8条） + Ohio-5（5条），合计约 13 条。

    卡片类型及字段覆盖：

    ================ ======= ======= ====== ===== ====
    卡片 testid       标题    描述    图片   时间  标签
    ================ ======= ======= ====== ===== ====
    london-card        ✅       —      ✅     ✅    ✅
    dundee-card        ✅       ✅      ✅     ✅    ✅
    manchester-card    ✅       ✅      —      ✅    ✅
    chester-card       ✅       —      —       —    —
    ================ ======= ======= ====== ===== ====

    统一选择器（所有卡片类型通用）：
    - 卡片: ``[data-testid$=\"-card\"]``
    - 标题: ``[data-testid=\"card-headline\"]``
    - 描述: ``[data-testid=\"card-description\"]``
    - 时间: ``[data-testid=\"card-metadata-lastupdated\"]``
    - 标签: ``[data-testid=\"card-metadata-tag\"]``
    - 图片: ``img``
    """

    extra_headers = {
        "Referer": "https://www.google.com/",
    }

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

            seen_urls: set[str] = set()
            items: List[CrawledItem] = []
            pos = 0

            for section_id in (_TOP_SECTION, _SECOND_SECTION):
                section = soup.select_one(f'[data-testid="{section_id}"]')
                if not section:
                    continue

                for card in section.select('[data-testid$="-card"]'):
                    link_el = card.select_one('a[href*="/news/"]')
                    if not link_el or not link_el.get("href"):
                        continue
                    href = link_el["href"]
                    if not href.startswith("http"):
                        href = urljoin(self.config.homepage, href)
                    if not any(p.search(href) for p in self.URL_FILTERS):
                        continue
                    if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    headline_el = card.select_one('[data-testid="card-headline"]')
                    title = (headline_el.get_text(strip=True) if headline_el else "").strip()
                    if not title or len(title) < 10:
                        continue

                    desc_el = card.select_one('[data-testid="card-description"]')
                    summary = (desc_el.get_text(strip=True) if desc_el else "")[:600]

                    time_el = card.select_one('[data-testid="card-metadata-lastupdated"]')
                    published_at = parse_relative_time(time_el.get_text(strip=True)) if time_el else None

                    img_el = card.select_one("img")
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

                if len(items) >= 50:
                    break

            result.items = items
            logger.info(f"BBC fetched {len(items)} items")
        except Exception as e:
            result.error = f"BBC fetch failed: {e}"
            logger.warning(result.error)
        return result