"""NewsContent model - on-demand full-article body cache."""
from datetime import datetime, timezone

from sqlalchemy import Column, Index, Integer, String

from ..database import Base


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class NewsContent(Base):
    __tablename__ = "news_contents"

    news_id = Column(Integer, primary_key=True)
    content_html = Column(String, nullable=False)
    content_text = Column(String, nullable=True)
    fetched_at = Column(String, default=_now, nullable=False)
    expires_at = Column(String, nullable=False)

    __table_args__ = (Index("idx_contents_expires", "expires_at"),)

    def to_dict(self) -> dict:
        return {
            "news_id": self.news_id,
            "content_html": self.content_html,
            "content_text": self.content_text,
            "fetched_at": self.fetched_at,
            "expires_at": self.expires_at,
        }