from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tabernas.config import Settings
from tabernas.main import create_app
from tabernas.sr.source import SrSource
from tests.support import TEST_DATABASE_URL, StubSource

FIXED_NOW = datetime(2026, 9, 27, 20, 0)
MakeClient = Callable[..., TestClient]


@pytest.fixture
def make_client(session_factory: sessionmaker[Session]) -> MakeClient:
    def _make(source: SrSource | None = None) -> TestClient:
        settings = Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL)  # type: ignore[call-arg]
        app = create_app(
            settings=settings,
            sr_source=source if source is not None else StubSource(),
            session_factory=session_factory,
            clock=lambda: FIXED_NOW,
        )
        return TestClient(app, raise_server_exceptions=False)

    return _make


@pytest.fixture
def client(make_client: MakeClient) -> TestClient:
    return make_client()
