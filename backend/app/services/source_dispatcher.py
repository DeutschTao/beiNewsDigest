"""Crawler dispatcher - chooses the right crawler based on source type/class."""
from __future__ import annotations

from typing import Optional

from .crawler.base import BaseCrawler, CrawlResult, SourceConfig
from .crawler.bbc import BBCCrawler
from .crawler.cnn import CNNCrawler
from .crawler.aljazeera import AlJazeeraCrawler
from .crawler.ap import APCrawler
from .crawler.reuters_rss import ReutersViaGoogleNewsRSS
from .crawler.generic_html import GenericHTMLCrawler
from .rss_adapter import RSSAdapter
from ..utils.logger import get_logger

logger = get_logger("crawler.dispatcher")


_CRAWLER_REGISTRY = {
    "BBCCrawler": BBCCrawler,
    "CNNCrawler": CNNCrawler,
    "AlJazeeraCrawler": AlJazeeraCrawler,
    "APCrawler": APCrawler,
    "ReutersViaGoogleNewsRSS": ReutersViaGoogleNewsRSS,
    "GenericHTMLCrawler": GenericHTMLCrawler,
    "RSSAdapter": RSSAdapter,
}


def get_crawler(source_config: SourceConfig) -> BaseCrawler:
    """Instantiate the right crawler for a given source."""
    code = source_config.crawler_class
    if code and code in _CRAWLER_REGISTRY:
        cls = _CRAWLER_REGISTRY[code]
        return cls(source_config)

    # Fallback based on source_type
    if source_config.type == "rss":
        return RSSAdapter(source_config)
    return GenericHTMLCrawler(source_config)


def register(name: str, cls: type) -> None:
    """Allow runtime registration of new crawler classes."""
    _CRAWLER_REGISTRY[name] = cls