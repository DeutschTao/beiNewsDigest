"""Crawler base class + result types."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from ...utils.logger import get_logger

logger = get_logger("crawler")


@dataclass
class CrawledItem:
    url: str
    title: str
    summary: str = ""
    cover_image: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    position: int = 0


@dataclass
class CrawlResult:
    source_code: str
    items: List[CrawledItem] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class SourceConfig:
    """Lightweight config carried into crawler constructors."""
    code: str
    name: str
    type: str
    homepage: Optional[str] = None
    rss_url: Optional[str] = None
    crawler_class: Optional[str] = None
    proxy: Optional[str] = None
    proxy_enabled: bool = False
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    @classmethod
    def from_db(cls, source_row, proxy: Optional[str], proxy_enabled: bool, timeout: int = 30) -> "SourceConfig":
        return cls(
            code=source_row.code,
            name=source_row.name,
            type=source_row.source_type,
            homepage=source_row.homepage_url,
            rss_url=source_row.rss_url,
            crawler_class=source_row.crawler_class,
            proxy=proxy,
            proxy_enabled=proxy_enabled,
            timeout=timeout,
        )

    @classmethod
    def from_yaml(cls, code: str, item, proxy: Optional[str], proxy_enabled: bool, timeout: int = 30) -> "SourceConfig":
        return cls(
            code=code,
            name=item.name,
            type=item.type,
            homepage=item.homepage,
            rss_url=item.rss_url,
            crawler_class=item.crawler_class,
            proxy=proxy,
            proxy_enabled=proxy_enabled,
            timeout=timeout,
        )


class BaseCrawler(ABC):
    """Abstract base class for list-level crawlers."""

    # Each subclass picks its own extra HTTP headers
    extra_headers: Dict[str, str] = {}

    def __init__(self, source_config: SourceConfig):
        self.config = source_config

    def _client_kwargs(self) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "timeout": httpx.Timeout(self.config.timeout),
            "follow_redirects": True,
            "headers": {
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                **self.extra_headers,
            },
        }
        if self.config.proxy_enabled and self.config.proxy:
            kwargs["proxy"] = self.config.proxy
        return kwargs

    def _new_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(**self._client_kwargs())

    @abstractmethod
    async def fetch_list(self) -> CrawlResult:
        ...

    async def fetch_content(self, url: str) -> Optional[str]:
        """On-demand fetch of article body. Subclasses may override with site-specific selectors."""
        try:
            async with self._new_client() as client:
                resp = await client.get(url)
                resp.raise_for_status()
                return self._extract_content_html(resp.text)
        except Exception as e:
            logger.warning(f"fetch_content failed for {url}: {e}")
            return None

    def _extract_content_html(self, raw_html: str) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(raw_html, "lxml")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()

        article = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find(attrs={"role": "article"})
        )
        if article is not None:
            return str(article)
        if soup.body is not None:
            for tag in soup.body(["nav", "header", "footer", "aside", "form"]):
                tag.decompose()
            return str(soup.body)
        return ""


def parse_relative_time(text: str) -> Optional[str]:
    """Parse relative time like '3 hrs ago', '19 mins ago', '5 hours ago' into ISO8601 UTC string.

    Falls back to parse_iso_date if text looks like an absolute date.
    Returns None if neither can be parsed.
    """
    if not text:
        return None
    text = text.strip()

    # Extract the first occurrence of a date pattern like "23 Jul 2026"
    # (handles duplicate text like "23 Jul 202623 Jul 2026" by taking the first match)
    date_match = re.search(r"(\d{1,2}\s+\w{3,9}\s+\d{4})", text)
    date_str = date_match.group(1) if date_match else text

    # Try absolute date parsing first (covers "23 Jul 2026", etc.)
    iso = parse_iso_date(date_str)
    if iso:
        return iso

    # Relative time parsing
    m = re.search(r"(\d+)\s*(hrs?|hours?|mins?|minutes?|days?)\s*ago", text, re.IGNORECASE)
    if not m:
        return None

    from datetime import datetime, timezone, timedelta

    num = int(m.group(1))
    unit = m.group(2).lower()
    now = datetime.now(timezone.utc)

    if unit in ("hr", "hrs", "hour", "hours"):
        dt = now - timedelta(hours=num)
    elif unit in ("min", "mins", "minute", "minutes"):
        dt = now - timedelta(minutes=num)
    elif unit in ("day", "days"):
        dt = now - timedelta(days=num)
    else:
        return None

    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    from bs4 import BeautifulSoup

    if not html:
        return ""
    text = BeautifulSoup(html, "lxml").get_text(" ")
    return re.sub(r"\s+", " ", text).strip()


def parse_iso_date(value: Any) -> Optional[str]:
    """Try to coerce a date-like value into ISO8601 UTC string."""
    if not value:
        return None
    if isinstance(value, str):
        # Try parsing any format via dateutil, then re-emit as ISO
        import dateutil.parser
        import dateutil.tz
        try:
            dt = dateutil.parser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dateutil.tz.UTC)
            return dt.astimezone(dateutil.tz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            return None
    try:
        import dateutil.parser
        import dateutil.tz
        dt = dateutil.parser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dateutil.tz.UTC)
        return dt.astimezone(dateutil.tz.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return None