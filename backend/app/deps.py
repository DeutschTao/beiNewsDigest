"""Shared FastAPI dependencies.

Session factory is initialized at startup (in main.py lifespan or module-level fallback).
Routers use this to get a per-request DB session.
"""
from typing import Callable, Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import load_config
from app.database import get_engine, get_session_factory

# Module-level initialization (also works with TestClient which skips lifespan)
_config = load_config()
_engine = get_engine(_config)
_session_factory = get_session_factory(_engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a DB session, auto-close on exit."""
    db = _session_factory()
    try:
        yield db
    finally:
        db.close()