from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, make_url, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from tabernas.db.models import Base
from tabernas.db.session import make_engine, make_session_factory
from tests.support import TEST_DATABASE_URL, reset_schema


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    database = make_url(TEST_DATABASE_URL).database or ""
    if not database.endswith("_test"):
        pytest.fail(f"TEST_DATABASE_URL debe apuntar a una base *_test, no a {database!r}")
    eng = make_engine(TEST_DATABASE_URL)
    try:
        eng.connect().close()
    except OperationalError:
        pytest.fail("Postgres de pruebas no disponible: corre `docker compose up -d db`")
    reset_schema(eng)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    yield make_session_factory(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE employee, rest_rule, schedule_exception, justification, setting "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def session(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as s:
        yield s
        s.rollback()
