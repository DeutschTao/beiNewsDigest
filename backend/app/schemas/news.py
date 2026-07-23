"""News schemas."""
from typing import Any, List, Optional

from pydantic import BaseModel


class NewsListItem(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    url: str
    published_at: Optional[str] = None
    source_id: Optional[int] = None
    source_code: Optional[str] = None
    source_name: Optional[str] = None


class NewsListResponse(BaseModel):
    items: List[NewsListItem]
    total: int
    page: int
    page_size: int


class NewsDetailResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    cover_image: Optional[str] = None
    url: str
    published_at: Optional[str] = None
    source_id: int
    source_code: str
    source_name: str
    has_full_content: bool = False
    content_html: Optional[str] = None
    content_source: str = "homepage"  # 'homepage' | 'fetched' | 'rss'
    fetched_at: Optional[str] = None


class HomeGroup(BaseModel):
    source_id: int
    source_code: str
    source_name: str
    items: List[NewsListItem]


class HomeResponse(BaseModel):
    groups: List[HomeGroup]
    updated_at: str
    total_sources: int