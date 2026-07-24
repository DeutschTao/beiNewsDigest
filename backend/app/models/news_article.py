"""NewsArticle model - list-level data from homepage/feed."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, UniqueConstraint

from ..database import Base


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_sort_at(published_at: str | None, fetched_at: str | None = None) -> str:
    """Compute the unified sort timestamp: use published_at if available, else fetched_at."""
    if published_at:
        return published_at
    return fetched_at or _now()


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, nullable=False, index=True)
    url = Column(String, nullable=False)
    url_hash = Column(String, nullable=False, unique=True)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=True)
    cover_image = Column(String, nullable=True)
    author = Column(String, nullable=True)
    published_at = Column(String, nullable=True)
    fetched_at = Column(String, default=_now, nullable=False)
    position = Column(Integer, default=0, nullable=False)
    sort_at = Column(String, nullable=False, index=True)

    __table_args__ = (
        Index("idx_articles_source_pos", "source_id", "position"),
        Index("idx_articles_sort", "sort_at"),
    )

    def to_dict(self, source: "NewsSource | None" = None) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "source_code": source.code if source else None,
            "source_name": source.name if source else None,
            "url": self.url,
            "title": self.title,
            "summary": self.summary,
            "cover_image": self.cover_image,
            "author": self.author,
            "published_at": self.published_at,
            "fetched_at": self.fetched_at,
            "sort_at": self.sort_at,
            "position": self.position,
        }