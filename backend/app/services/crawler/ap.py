"""AP News World homepage crawler (apnews.com/world-news)."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, get_logger

logger = get_logger("crawler.ap")


class APCrawler(BaseCrawler):
    """专抓 https://apnews.com/world-news 第一个板块（.TwoColumnContainer7030）。

    抓取范围：
    - 左列 (70%)：PageList-items-item → 5 条要闻
    - 右列 (30%)：Most Read → 5 条热门

    左列卡片 DOM::

        <div class="PageList-items-item">
          <div class="PagePromo">
            <div class="PagePromo-media">
              <a class="Link"><img src="..."></a>
            </div>
            <div class="PagePromo-content">
              <bsp-custom-headline><h2>标题</h2></bsp-custom-headline>
              <div class="PagePromo-description">摘要</div>
              <div class="PagePromo-byline-container">时间/署名</div>
            </div>
          </div>
        </div>

    右列 Most Read DOM::

        <div class="PageListRightRailA">
          <a href="/article/...">文章标题</a>
          <a href="/article/...">阅读量数字</a>
          ... (每篇文章两个相同链接，需去重)
        </div>
    """

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

            block = soup.select_one(".TwoColumnContainer7030")
            if not block:
                result.error = "TwoColumnContainer7030 not found"
                return result

            seen_urls: set[str] = set()
            items: List[CrawledItem] = []
            pos = 0

            # ---- 左列：PageList-items-item ----
            for promo in block.select(".PageList-items-item"):
                # 链接：取 PagePromo-content 区域的 a 标签（避免取到图片区的 a）
                content_area = promo.select_one(".PagePromo-content")
                link_el = content_area.select_one("a[href]") if content_area else promo.select_one("a[href]")
                if not link_el or not link_el.get("href"):
                    continue
                href = link_el["href"]
                if href.startswith("/"):
                    href = urljoin(self.config.homepage, href)
                if not any(p.search(href) for p in self.URL_FILTERS):
                    continue
                if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                # 标题：bsp-custom-headline
                headline_el = promo.select_one("bsp-custom-headline")
                title = (headline_el.get_text(strip=True) if headline_el else "").strip()
                if not title or len(title) < 10:
                    continue

                # 摘要
                desc_el = promo.select_one(".PagePromo-description")
                summary = (desc_el.get_text(strip=True) if desc_el else "")[:600]

                # 封面图
                img_el = promo.select_one(".PagePromo-media img")
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

            # ---- 右列：Most Read (PageListRightRailA) ----
            right_rail = block.select_one(".PageListRightRailA")
            if right_rail:
                for a in right_rail.select('a[href*="/article/"]'):
                    href = a.get("href", "")
                    if not href:
                        continue
                    if href.startswith("/"):
                        href = urljoin(self.config.homepage, href)
                    if not any(p.search(href) for p in self.URL_FILTERS):
                        continue
                    if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    title = a.get_text(strip=True)
                    # 跳过纯数字（阅读量）
                    if not title or title.isdigit() or len(title) < 10:
                        continue

                    pos += 1
                    items.append(CrawledItem(
                        url=href,
                        title=title,
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