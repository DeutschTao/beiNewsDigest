"""NewsSource model."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from ..database import Base


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NewsSource(Base):
    __tablename__ = "news_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # 'crawler' | 'rss'
    homepage_url = Column(String, nullable=True)
    rss_url = Column(String, nullable=True)
    category = Column(String, default="world", nullable=False)
    crawler_class = Column(String, nullable=True)
    is_enabled = Column(Integer, default=1, nullable=False)
    is_recommended = Column(Integer, default=0, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    created_at = Column(String, default=_now, nullable=False)
    updated_at = Column(String, default=_now, onupdate=_now, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "source_type": self.source_type,
            "homepage_url": self.homepage_url,
            "rss_url": self.rss_url,
            "category": self.category,
            "crawler_class": self.crawler_class,
            "is_enabled": bool(self.is_enabled),
            "is_recommended": bool(self.is_recommended),
            "display_order": self.display_order,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }