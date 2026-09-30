"""Against the real SR server. Local only: `uv run pytest -m sr tests/sr/test_live.py`."""

from datetime import date

import pytest

from tabernas.config import Settings
from tabernas.sr.pymssql_source import PymssqlSource

pytestmark = pytest.mark.sr


@pytest.fixture
def live_source() -> PymssqlSource:
    return PymssqlSource.from_settings(Settings(sr_mode="live"))


def test_login_is_read_only(live_source: PymssqlSource) -> None:
    assert live_source.server_info().read_only


def test_reads_one_week_of_checkins(live_source: PymssqlSource) -> None:
    checkins = live_source.fetch_checkins(date(2026, 8, 3), date(2026, 8, 9))
    assert checkins
    assert all(date(2026, 8, 3) <= c.at.date() <= date(2026, 8, 9) for c in checkins)


def test_reads_employees(live_source: PymssqlSource) -> None:
    assert live_source.fetch_employees()
