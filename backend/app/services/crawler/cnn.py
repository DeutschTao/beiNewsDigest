"""CNN World homepage crawler (edition.cnn.com/world)."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, get_logger

logger = get_logger("crawler.cnn")

# CNN card 中图片署名的噪音模式（不应作为标题）
_TITLE_NOISE_PATTERNS = re.compile(
    r"(Getty Images|AFP|AFP/Getty|Reuters|AP Photo|EPA|EFE|"
    r"Press Service|Handout|Pool Photo|Anadolu)",
    re.IGNORECASE,
)


class CNNCrawler(BaseCrawler):
    """专抓 https://edition.cnn.com/world 的第一个 zone 模块的新闻卡片。

    卡片 DOM 结构::

        <li class="card container__item container__item--type-media-image ...">
          <a class="container__link ..." href="/2026/07/24/world/...">
            <img src="...">
            图片署名 (噪音)
          </a>
          <span class="container__headline-text">新闻标题</span>
        </li>

    抓取范围：
    - 页面第一个 zone（data-component-name="zone"）内的所有 li.card
    - 不包含时间戳（此视图不展示时间）
    - 不包含摘要（卡片级不提供摘要）
    """

    extra_headers = {
        "Referer": "https://www.google.com/",
    }

    URL_FILTERS = (re.compile(r"\.cnn\.com"),)
    SKIP_KEYWORDS = (
        "/videos/", "/video/", "/live/",          # 视频 / 直播流
        "/audio/", "/newsletters", "/account",     # 音频 / 简报 / 账户
        "/style/", "/travel/",                     # 非新闻频道
    )

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

            # 只取页面第一个 zone 模块内的新闻卡片（约15条）
            # 后续如需扩展其他 zone，改为遍历所有 div.zone 即可
            first_zone = soup.select_one("div.zone")
            zone_cards = first_zone.select("li.card.container__item") if first_zone else []
            for card in zone_cards:
                # ---- 链接：取 a.container__link 而非图片的 <a> ----
                link_el = card.select_one('a[class*="container__link"]')
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

                # ---- 标题：span.container__headline-text ----
                headline_el = card.select_one('span[class*="headline-text"]')
                title = (headline_el.get_text(strip=True) if headline_el else "").strip()
                if not title or len(title) < 10:
                    continue
                if _TITLE_NOISE_PATTERNS.search(title) and len(title) < 30:
                    continue

                # ---- 封面图 ----
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
                    cover_image=cover,
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
