from datetime import datetime

from fastapi.testclient import TestClient

from tabernas.config import Settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.main import create_app
from tabernas.sr.source import SrUnavailableError
from tests.api.conftest import MakeClient
from tests.support import READ_ONLY_INFO, TEST_DATABASE_URL, StubSource


def test_health_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": {"status": "ok", "db": "ok"},
        "error": None,
        "meta": None,
    }


def test_health_reports_database_down() -> None:
    unreachable = make_session_factory(make_engine("postgresql+psycopg://x:x@127.0.0.1:1/none"))
    app = create_app(
        settings=Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL),  # type: ignore[call-arg]
        sr_source=StubSource(),
        session_factory=unreachable,
        clock=lambda: datetime(2026, 9, 27, 20, 0),
    )
    body = TestClient(app, raise_server_exceptions=False).get("/health").json()
    assert body["data"] == {"status": "degraded", "db": "error"}


def test_health_sr_reports_server(client: TestClient) -> None:
    data = client.get("/health/sr").json()["data"]
    assert data["mode"] == "fake"
    assert data["version"] == "12.0.4100.1"
    assert data["is_sysadmin"] is False


def test_health_sr_refuses_writable_login(make_client: MakeClient) -> None:
    writable = READ_ONLY_INFO.model_copy(update={"is_denywriter": False})
    response = make_client(StubSource(info=writable)).get("/health/sr")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "SR_NOT_READONLY"


def test_health_sr_unavailable(make_client: MakeClient) -> None:
    response = make_client(StubSource(error=SrUnavailableError("x"))).get("/health/sr")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SR_UNAVAILABLE"
    assert "Tailscale" in response.json()["error"]["message"]
