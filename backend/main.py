"""FastAPI application entry point."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_config
from app.database import get_engine, get_session_factory
from app.routers import home, news, proxy, sources, trigger
from app.tasks.cleanup_task import run_cleanup
from app.tasks.fetch_task import fetch_all_sources
from app.tasks.scheduler import TimeBasedScheduler
from app.utils.exceptions import install_exception_handlers
from app.utils.logger import logger

_scheduler: TimeBasedScheduler | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _scheduler
    config = load_config()
    logger.info(f"App starting, db={config.database.url}, proxy={'on' if config.fetch.proxy_enabled else 'off'}")

    # Initialize DB + seed preset sources
    from init_db import _init_database
    _init_database()

    # Initialize engine/session factory for request scope
    engine = get_engine(config)
    app.state.session_factory = get_session_factory(engine)

    # Start scheduler
    if config.scheduler.enabled:
        async def run_fetch(db, cfg):
            return await fetch_all_sources(db, cfg, sleep_between=True)

        _scheduler = TimeBasedScheduler(config, run_fetch)
        await _scheduler.start()
        logger.info("Scheduler started")

    yield

    # Shutdown
    if _scheduler:
        await _scheduler.stop()
    logger.info("App shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Bei News Digest v2",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_exception_handlers(app)

    # Routers
    app.include_router(home.router)
    app.include_router(news.router)
    app.include_router(sources.router)
    app.include_router(trigger.router)
    app.include_router(proxy.router)

    @app.get("/api/v2/health")
    async def health():
        from sqlalchemy import text
        from app.database import _engine
        try:
            if _engine is not None:
                with _engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {e}"
        return {"code": 0, "message": "success", "data": {
            "status": "healthy" if db_status == "connected" else "degraded",
            "database": db_status,
            "version": "2.0.0",
        }}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    config = load_config()
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
        log_level=config.server.log_level,
    )