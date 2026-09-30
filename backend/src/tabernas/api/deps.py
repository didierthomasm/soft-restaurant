"""Request-scoped dependencies. The session commits before the response is sent."""

from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from tabernas.config import Settings
from tabernas.sr.source import SrSource


def get_session(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


def get_sr_source(request: Request) -> SrSource:
    return request.app.state.sr_source


def get_clock(request: Request) -> Callable[[], datetime]:
    return request.app.state.clock


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


# scope="function": commit runs right after the route returns, before the response is
# sent, so a failed commit becomes an error response instead of a silent loss.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]
SrSourceDep = Annotated[SrSource, Depends(get_sr_source)]
ClockDep = Annotated[Callable[[], datetime], Depends(get_clock)]
AppSettingsDep = Annotated[Settings, Depends(get_app_settings)]
