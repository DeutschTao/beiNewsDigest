"""Al Jazeera homepage crawler (www.aljazeera.com)."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, parse_relative_time, get_logger

logger = get_logger("crawler.aljazeera")


class AlJazeeraCrawler(BaseCrawler):
    """专抓 https://www.aljazeera.com/ 首页第一个板块（#featured-news-container）。

    抓取范围：
    - Liveblog 时间线各条目（ul.liveblog-timeline > li.liveblog-timeline__update）
    - 普通新闻卡片（article.article-card，含 hp-featured-second-stories / categories）

    Liveblog 条目 DOM 结构::

        <li class="liveblog-timeline__update">
          <div class="liveblog-timeline__update-details">
            <span class="liveblog-timeline__update-display-time">9m ago</span>
            <a class="liveblog-timeline__update-link" href="...?update=xxx">
              <h3 class="liveblog-timeline__update-content">新闻标题</h3>
            </a>
          </div>
        </li>

    普通卡片 DOM 结构::

        <article class="article-card ...">
          <a class="article-card__link" href="/news/2026/7/24/...">
            <img src="...">
            <div class="article-card__title">标题</div>
            <div class="article-card__excerpt">摘要</div>
          </a>
        </article>
    """

    extra_headers = {
        "Referer": "https://www.google.com/",
    }

    URL_FILTERS = (re.compile(r"aljazeera\.com"),)
    SKIP_KEYWORDS = ("/videos/", "/video/", "/live/", "/podcasts", "/gallery", "/infographic")

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

            featured = soup.select_one("#featured-news-container")
            if not featured:
                result.error = "featured-news-container not found"
                return result

            seen_urls: set[str] = set()
            items: List[CrawledItem] = []
            pos = 0

            # ---- Part 0: Liveblog 主文章（第一个大卡片） ----
            liveblog_card = featured.select_one("article.article-card__liveblog")
            if liveblog_card:
                main_link = liveblog_card.select_one("a.u-clickable-card__link")
                if main_link and main_link.get("href"):
                    href = main_link["href"]
                    if href.startswith("/"):
                        href = urljoin(self.config.homepage, href)
                    if any(p.search(href) for p in self.URL_FILTERS) and href not in seen_urls:
                        seen_urls.add(href)

                        title_el = liveblog_card.select_one(
                            "[class*='article-card__liveblog-title'], [class*='article-card__title']"
                        )
                        raw_title = (title_el.get_text(strip=True) if title_el else "").strip()
                        # 清洗 "BREAKINGBREAKING," → "BREAKING,"
                        title = re.sub(r"^(BREAKING)+", "BREAKING", raw_title)

                        img_el = liveblog_card.select_one("img")
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

            # ---- Part 1: Liveblog 时间线各条目 ----
            for li in featured.select("li.liveblog-timeline__update"):
                link_el = li.select_one("a.liveblog-timeline__update-link")
                title_el = li.select_one("h3.liveblog-timeline__update-content")
                time_el = li.select_one("span.liveblog-timeline__update-display-time")

                if not link_el or not link_el.get("href"):
                    continue
                href = link_el["href"]
                if href.startswith("/"):
                    href = urljoin(self.config.homepage, href)
                if not any(p.search(href) for p in self.URL_FILTERS):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                title = (title_el.get_text(strip=True) if title_el else "").strip()
                if not title or len(title) < 5:
                    continue
                # 跳过 "Photos:" 开头的图集条目
                if title.lower().startswith("photos:"):
                    continue
                    continue

                published_at = parse_relative_time(time_el.get_text(strip=True)) if time_el else None

                pos += 1
                items.append(CrawledItem(
                    url=href,
                    title=title,
                    published_at=published_at,
                    position=pos,
                ))
                if len(items) >= 50:
                    break

            # ---- Part 2: 普通 article-card ----
            for card in featured.select("article.article-card:not([class*='liveblog'])"):
                link_el = card.select_one("a.article-card__link")
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

                title_el = card.select_one("[class*='article-card__title']")
                title = (title_el.get_text(strip=True) if title_el else "").strip()
                if not title or len(title) < 10:
                    continue

                excerpt_el = card.select_one("[class*='article-card__excerpt']")
                summary = (excerpt_el.get_text(strip=True) if excerpt_el else "")[:600]

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
                    position=pos,
                ))
                if len(items) >= 50:
                    break

            result.items = items
            logger.info(f"Al Jazeera fetched {len(items)} items")
        except Exception as e:
            result.error = f"Al Jazeera fetch failed: {e}"
            logger.warning(result.error)
        return result