"""Initialize database: create tables and seed preset sources from config."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session

from app.config import load_config
from app.database import Base, get_engine, get_session_factory
from app.models import NewsSource
from app.utils.logger import logger


def _init_database(db_url: str | None = None) -> None:
    config = load_config()
    if db_url:
        config.database.url = db_url
    engine = get_engine(config)
    SessionFactory = get_session_factory(engine)

    Base.metadata.create_all(engine)
    logger.info("Database tables created successfully")

    session: Session = SessionFactory()
    try:
        existing = session.query(NewsSource).count()
        if existing > 0:
            logger.info(f"Database already has {existing} sources, skipping seed")
            return

        if not config.news_sources:
            logger.warning("No news sources defined in config.yaml")
            return

        for order, (code, item) in enumerate(config.news_sources.items(), start=1):
            src = NewsSource(
                code=code,
                name=item.name,
                source_type=item.type,
                homepage_url=item.homepage,
                rss_url=item.rss_url,
                category=item.category or "world",
                crawler_class=item.crawler_class,
                is_enabled=1 if item.enabled else 0,
                is_recommended=1 if item.is_recommended else 0,
                display_order=item.display_order or order,
            )
            session.add(src)
        session.commit()
        logger.info(f"Seeded {len(config.news_sources)} preset news sources from config")
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to seed data: {e}")
        raise
    finally:
        session.close()

    logger.info(f"Database initialized: {config.database.url}")


if __name__ == "__main__":
    _init_database()