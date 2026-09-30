from datetime import UTC, datetime, tzinfo

from tabernas.config import Settings
from tabernas.main import create_app, local_clock
from tabernas.sr.fake_source import FakeSource
from tests.support import TEST_DATABASE_URL


def test_local_clock_uses_business_timezone() -> None:
    # Review Focus #3: 05:30 UTC on the 28th is still 23:30 on the 27th in Monterrey.
    instant = datetime(2026, 9, 28, 5, 30, tzinfo=UTC)

    def fake_now(tz: tzinfo) -> datetime:
        return instant.astimezone(tz)

    clock = local_clock("America/Mexico_City", now=fake_now)
    assert clock() == datetime(2026, 9, 27, 23, 30)


def test_fake_mode_wires_fake_source_without_touching_services() -> None:
    settings = Settings(_env_file=None, sr_mode="fake", database_url=TEST_DATABASE_URL)  # type: ignore[call-arg]
    app = create_app(settings=settings)
    assert isinstance(app.state.sr_source, FakeSource)
