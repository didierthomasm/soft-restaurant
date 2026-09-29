"""FastAPI application factory. Run with: uvicorn --factory tabernas.main:create_app"""

from collections.abc import Callable
from datetime import datetime, tzinfo
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from tabernas.api.errors import register_error_handlers
from tabernas.api.routes import ROUTERS
from tabernas.config import Settings, get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.sr import build_sr_source
from tabernas.sr.source import SrSource


def local_clock(
    tz_name: str, now: Callable[[tzinfo], datetime] = datetime.now
) -> Callable[[], datetime]:
    """Naive local time in the business timezone, comparable with SR's naive datetimes."""
    zone = ZoneInfo(tz_name)
    return lambda: now(zone).replace(tzinfo=None)


def create_app(
    *,
    settings: Settings | None = None,
    sr_source: SrSource | None = None,
    session_factory: sessionmaker[Session] | None = None,
    clock: Callable[[], datetime] | None = None,
) -> FastAPI:
    resolved = settings or get_settings()
    app = FastAPI(title="Tabernas Cerveceras API", version="0.1.0")
    app.state.settings = resolved
    app.state.sr_source = sr_source if sr_source is not None else build_sr_source(resolved)
    app.state.session_factory = session_factory or make_session_factory(
        make_engine(resolved.database_url)
    )
    app.state.clock = clock or local_clock(resolved.app_timezone)
    register_error_handlers(app)
    for router in ROUTERS:
        app.include_router(router)
    return app
