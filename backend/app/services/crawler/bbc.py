"""BBC News crawler — 国际版 + UK版双策略兜底.

- BBCCrawler: 国际版 (bbc.com) data-testid 选择器，13条
- BBCCoCrawlerUK: UK版 (bbc.co.uk) #nations-news-uk 选择器，12条

BBCCrawler.fetch_list() 自动检测：
  若 homepage 为 .co.uk 且未被重定向 → 用 UK 策略
  若 homepage 为 .co.uk 但被重定向到 .com → 回退国际版策略
  若 homepage 为 .com → 直接用国际版策略
"""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, parse_relative_time, get_logger

logger = get_logger("crawler.bbc")

# ---- 国际版常量 ----
_INTL_TOP = "virginia-section-outer-8"
_INTL_SECOND = "ohio-section-outer-5"


# ============================================================================
# BBCCoCrawlerUK — UK版
# ============================================================================

# 匹配 "Video, 00:01:25" 及其之后的所有重复文本
_UK_VIDEO_SUFFIX = re.compile(r"\bVideo,\s*\d{1,2}:\d{2}(:\d{2})?\s*.*", re.IGNORECASE)
_UK_LIVE_PREFIX = re.compile(r"^Live\.\s*")


class BBCCoCrawlerUK(BaseCrawler):
    """抓取 bbc.co.uk/news 的 #nations-news-uk 区域，约12条。

    适配 BBC UK Next.js 架构，卡片为直接 <a> 链接，无 data-testid。
    标题和图片从 <a> 标签及其祖先节点提取。
    """

    extra_headers = {"Referer": "https://www.google.com/"}
    URL_FILTERS = (
        re.compile(r"/news/articles/"),
        re.compile(r"/news/live/"),
        re.compile(r"/news/videos/"),
        re.compile(r"/sport/"),
        re.compile(r"/weather/"),
    )
    SKIP_KEYWORDS = ("/podcasts/", "/sounds/", "iplayer")

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

            uk = soup.select_one("#nations-news-uk")
            if not uk:
                result.error = "nations-news-uk not found"
                return result

            seen_urls: set[str] = set()
            items: List[CrawledItem] = []
            pos = 0

            for a in uk.select("a[href]"):
                href = a.get("href", "")
                if not href or href.startswith("#"):
                    continue
                if not href.startswith("http"):
                    href = urljoin(self.config.homepage, href)
                if not any(p.search(href) for p in self.URL_FILTERS):
                    continue
                if any(k in href.lower() for k in self.SKIP_KEYWORDS):
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                raw = a.get_text(strip=True)
                # 跳过分类标签（短文本如 "Asia", "Business"）和评论数
                if not raw or len(raw) < 15 or raw.isdigit():
                    continue

                # 清洗标题：去 Video 时长尾缀、去 Live. 前缀
                title = _UK_VIDEO_SUFFIX.sub("", raw).strip()
                title = _UK_LIVE_PREFIX.sub("", title).strip()
                if len(title) < 10:
                    continue

                # 向上查找封面图和相对时间
                img_el = None
                time_text = ""
                parent = a.parent
                for _ in range(8):
                    if parent and hasattr(parent, "name") and parent.name:
                        if not img_el:
                            imgs = parent.select("img")
                            if imgs:
                                img_el = imgs[0]
                        if not time_text:
                            time_span = parent.select_one('span[class*="visually-hidden"]')
                            if time_span:
                                txt = time_span.get_text(strip=True)
                                if any(w in txt.lower() for w in ("ago", "hour", "min", "minute")):
                                    time_text = txt
                    parent = parent.parent if parent else None

                cover = None
                if img_el:
                    cover = img_el.get("src") or img_el.get("data-src")
                    if cover and cover.startswith("/"):
                        cover = urljoin(self.config.homepage, cover)

                published_at = parse_relative_time(time_text) if time_text else None

                pos += 1
                items.append(CrawledItem(
                    url=href,
                    title=title,
                    cover_image=cover,
                    published_at=published_at,
                    position=pos,
                ))
                if len(items) >= 50:
                    break

            result.items = items
            logger.info(f"BBC UK fetched {len(items)} items")
        except Exception as e:
            result.error = f"BBC UK fetch failed: {e}"
            logger.warning(result.error)
        return result


# ============================================================================
# BBCCrawler — 国际版 + UK 兜底
# ============================================================================

class BBCCrawler(BaseCrawler):
    """BBC 国际版抓取 + UK 版自动兜底.

    策略：
    1. 若 homepage 含 .co.uk → 先尝试 UK 策略
    2. 若 UK 版被重定向到 .com → 回退国际版
    3. 若 homepage 含 .com → 直接用国际版
    """

    extra_headers = {"Referer": "https://www.google.com/"}
    URL_FILTERS = (
        re.compile(r"/news/articles/"),
        re.compile(r"/sport/"),
    )
    SKIP_KEYWORDS = ("/videos/", "/live/", "/podcasts/", "/sounds/", "iplayer")

    async def fetch_list(self) -> CrawlResult:
        is_uk = "bbc.co.uk" in (self.config.homepage or "")

        if is_uk:
            # 第一步：尝试 UK 版
            uk_result = await self._try_uk()
            if uk_result is not None:
                return uk_result
            logger.info("BBC .co.uk redirected to .com, falling back to international")

        # 第二步：国际版
        return await self._fetch_intl()

    async def _try_uk(self) -> CrawlResult | None:
        """尝试 UK 版抓取，若未被重定向则返回结果，否则返回 None."""
        try:
            async with self._new_client() as client:
                resp = await client.get(self.config.homepage)
                resp.raise_for_status()

                # 检查是否被重定向
                final_url = str(resp.url)
                if "bbc.co.uk" not in final_url:
                    return None

                soup = BeautifulSoup(resp.text, "lxml")
                uk = soup.select_one("#nations-news-uk")
                if not uk:
                    return None

                seen_urls: set[str] = set()
                items: List[CrawledItem] = []
                pos = 0

                for a in uk.select("a[href]"):
                    href = a.get("href", "")
                    if not href or href.startswith("#"):
                        continue
                    if not href.startswith("http"):
                        href = urljoin(self.config.homepage, href)
                    if not any(p.search(href) for p in _UK_URL_FILTERS):
                        continue
                    if any(k in href.lower() for k in _UK_SKIP_KEYWORDS):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    raw = a.get_text(strip=True)
                    if not raw or len(raw) < 15 or raw.isdigit():
                        continue

                    title = _UK_VIDEO_SUFFIX.sub("", raw).strip()
                    title = _UK_LIVE_PREFIX.sub("", title).strip()
                    if len(title) < 10:
                        continue

                    img_el = None
                    time_text = ""
                    parent = a.parent
                    for _ in range(8):
                        if parent and hasattr(parent, "name") and parent.name:
                            if not img_el:
                                imgs = parent.select("img")
                                if imgs:
                                    img_el = imgs[0]
                            if not time_text:
                                time_span = parent.select_one('span[class*="visually-hidden"]')
                                if time_span:
                                    txt = time_span.get_text(strip=True)
                                    if any(w in txt.lower() for w in ("ago", "hour", "min", "minute")):
                                        time_text = txt
                        parent = parent.parent if parent else None

                    cover = None
                    if img_el:
                        cover = img_el.get("src") or img_el.get("data-src")
                        if cover and cover.startswith("/"):
                            cover = urljoin(self.config.homepage, cover)

                    published_at = parse_relative_time(time_text) if time_text else None

                    pos += 1
                    items.append(CrawledItem(
                        url=href,
                        title=title,
                        cover_image=cover,
                        published_at=published_at,
                        position=pos,
                    ))
                    if len(items) >= 50:
                        break

                result = CrawlResult(source_code=self.config.code)
                result.items = items
                logger.info(f"BBC UK fetched {len(items)} items")
                return result

        except Exception as e:
            logger.warning(f"BBC UK attempt failed: {e}")
            return None

    async def _fetch_intl(self) -> CrawlResult:
        """国际版抓取."""
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

            for section_id in (_INTL_TOP, _INTL_SECOND):
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

            result.items = items
            logger.info(f"BBC intl fetched {len(items)} items")
        except Exception as e:
            result.error = f"BBC fetch failed: {e}"
            logger.warning(result.error)
        return result


# ---- UK 版常量（BBCCrawler 内联使用）----
_UK_URL_FILTERS = (
    re.compile(r"/news/articles/"),
    re.compile(r"/news/live/"),
    re.compile(r"/news/videos/"),
    re.compile(r"/sport/"),
    re.compile(r"/weather/"),
)
_UK_SKIP_KEYWORDS = ("/podcasts/", "/sounds/", "iplayer")
_UK_VIDEO_SUFFIX = re.compile(r"\bVideo,\s*\d{1,2}:\d{2}(:\d{2})?\s*.*", re.IGNORECASE)