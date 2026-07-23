"""Configuration loader - YAML → Pydantic models."""
import os
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8001
    reload: bool = True
    log_level: str = "info"


class DatabaseConfig(BaseModel):
    url: str = "sqlite:///./data/bei_news_v2.db"
    echo: bool = False


class ScheduleSlot(BaseModel):
    start: str
    end: str
    interval_minutes: int


class FetchConfig(BaseModel):
    proxy_enabled: bool = True
    proxy: Optional[str] = None
    timeout: int = 30
    max_items_per_source: int = 50
    min_source_interval: int = 600
    jitter_seconds: int = 30
    rate_limit_seconds: Tuple[int, int] = (5, 30)
    schedule: List[ScheduleSlot] = Field(default_factory=list)


class NewsExpiryConfig(BaseModel):
    home_window_hours: int = 24
    list_window_hours: int = 168
    max_age_hours: int = 48
    content_cache_hours: int = 24
    retention_days: int = 7


class NewsSourceItem(BaseModel):
    type: str  # 'crawler' | 'rss'
    name: str
    homepage: Optional[str] = None
    rss_url: Optional[str] = None
    category: str = "world"
    crawler_class: Optional[str] = None
    is_recommended: bool = True
    display_order: int = 0
    enabled: bool = True


class ContentFetcherConfig(BaseModel):
    enabled: bool = True
    proxy_enabled: bool = True
    proxy: Optional[str] = None
    timeout: int = 30
    user_agent: str = "Mozilla/5.0"
    # 是否强制拉取正文（开启时无视 summary 长度，关闭时走 summary_length_threshold 策略）
    force_fetch: bool = False
    # summary 长度低于此阈值时才拉取正文（仅在 force_fetch=false 时生效）
    summary_length_threshold: int = 300


class SchedulerConfig(BaseModel):
    enabled: bool = True
    cleanup_cron: str = "0 5 * * *"


class ApiConfig(BaseModel):
    max_sources: int = 50
    custom_source_validate_timeout: int = 8


class AppConfig(BaseModel):
    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    fetch: FetchConfig = FetchConfig()
    news_expiry: NewsExpiryConfig = NewsExpiryConfig()
    news_sources: Dict[str, NewsSourceItem] = Field(default_factory=dict)
    content_fetcher: ContentFetcherConfig = ContentFetcherConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    api: ApiConfig = ApiConfig()

    def get_proxy(self) -> Optional[str]:
        return self.fetch.proxy if self.fetch.proxy_enabled else None


_CONFIG_PATH = os.environ.get("BEI_NEWS_CONFIG", os.path.join(os.path.dirname(__file__), "..", "config.yaml"))


def load_config(path: str | None = None) -> AppConfig:
    path = path or _CONFIG_PATH
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if not os.path.exists(path):
        # Return defaults if config missing (so init_db / tests can run)
        return AppConfig()
    with open(path, "r", encoding="utf-8") as f:
        raw: Dict[str, Any] = yaml.safe_load(f) or {}
    sources_raw = raw.get("news_sources", {}) or {}
    return AppConfig(
        server=ServerConfig(**(raw.get("server") or {})),
        database=DatabaseConfig(**(raw.get("database") or {})),
        fetch=FetchConfig(**(raw.get("fetch") or {})),
        news_expiry=NewsExpiryConfig(**(raw.get("news_expiry") or {})),
        news_sources={k: NewsSourceItem(**v) for k, v in sources_raw.items()},
        content_fetcher=ContentFetcherConfig(**(raw.get("content_fetcher") or {})),
        scheduler=SchedulerConfig(**(raw.get("scheduler") or {})),
        api=ApiConfig(**(raw.get("api") or {})),
    )