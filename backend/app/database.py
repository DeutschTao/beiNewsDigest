"""SQLAlchemy engine + ORM base + session factory."""
import os
from typing import Callable

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import AppConfig
from .utils.logger import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionFactory: Callable[[], Session] | None = None


def _ensure_data_dir(db_url: str) -> None:
    """Create the data/ directory for sqlite file-based URLs."""
    if not db_url.startswith("sqlite:///"):
        return
    path = db_url.replace("sqlite:///", "", 1)
    if path.startswith("./") or path.startswith("../"):
        path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def get_engine(config: AppConfig) -> Engine:
    global _engine
    if _engine is not None:
        return _engine

    db_url = config.database.url
    _ensure_data_dir(db_url)

    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

    _engine = create_engine(
        db_url,
        echo=config.database.echo,
        connect_args=connect_args,
        future=True,
    )

    # Enable WAL mode for SQLite (better concurrent read/write)
    if db_url.startswith("sqlite"):
        @event.listens_for(_engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    logger.info(f"Database engine initialized: {db_url}")
    return _engine


def get_session_factory(engine: Engine | None = None) -> Callable[[], Session]:
    global _SessionFactory
    if _SessionFactory is not None and engine is None:
        return _SessionFactory
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call get_engine() first.")
    _SessionFactory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, future=True)
    return _SessionFactory


def reset_engine() -> None:
    """Used by tests to force re-init."""
    global _engine, _SessionFactory
    _engine = None
    _SessionFactory = None