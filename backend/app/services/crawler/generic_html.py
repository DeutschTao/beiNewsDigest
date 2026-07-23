"""Generic HTML crawler for user-added custom HTML sources."""
from __future__ import annotations

import re
from typing import List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseCrawler, CrawlResult, CrawledItem, get_logger

logger = get_logger("crawler.generic")


class GenericHTMLCrawler(BaseCrawler):
    """Generic HTML extractor using og: meta tags and common semantics."""

    TITLE_SELECTORS = [
        ('meta[property="og:title"]', "content"),
        ('meta[name="twitter:title"]', "content"),
        ('meta[name="title"]', "content"),
    ]

    SUMMARY_SELECTORS = [
        ('meta[property="og:description"]', "content"),
        ('meta[name="twitter:description"]', "content"),
        ('meta[name="description"]', "content"),
    ]

    COVER_SELECTORS = [
        ('meta[property="og:image"]', "content"),
        ('meta[name="twitter:image"]', "content"),
    ]

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

            title = self._pick_meta(soup, self.TITLE_SELECTORS)
            if not title:
                # fallback to h1
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else self.config.name

            summary = self._pick_meta(soup, self.SUMMARY_SELECTORS) or ""

            cover = self._pick_meta(soup, self.COVER_SELECTORS)
            if not cover:
                img = soup.find("img")
                if img and img.get("src"):
                    cover = img["src"]
                    if cover.startswith("/"):
                        cover = urljoin(self.config.homepage, cover)

            result.items.append(CrawledItem(
                url=self.config.homepage,
                title=title.strip(),
                summary=summary.strip()[:600],
                cover_image=cover,
                position=1,
            ))
            logger.info(f"Generic HTML fetched {len(result.items)} item(s) for {self.config.code}")
        except Exception as e:
            result.error = f"Generic HTML fetch failed: {e}"
            logger.warning(result.error)
        return result

    def _pick_meta(self, soup: BeautifulSoup, selectors) -> Optional[str]:
        for sel, attr in selectors:
            tag = soup.select_one(sel)
            if tag and tag.get(attr):
                value = tag[attr].strip()
                if value:
                    return value
        return None