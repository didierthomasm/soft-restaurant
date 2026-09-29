import os
from collections.abc import Sequence
from datetime import date

from sqlalchemy import Engine, text

from tabernas.sr.source import SrCheckin, SrEmployee, SrServerInfo

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://tabernas:tabernas@localhost:5432/tabernas_test"
)

READ_ONLY_INFO = SrServerInfo(
    server="SRV",
    instance="INST",
    version="12.0.4100.1",
    edition="Express Edition",
    database="softrestaurant11",
    login="reportes_ro",
    is_datareader=True,
    is_denywriter=True,
    is_sysadmin=False,
)


def reset_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))


class StubSource:
    """SrSource test double: canned data, optional error, records check-in calls."""

    def __init__(
        self,
        *,
        employees: Sequence[SrEmployee] = (),
        checkins: Sequence[SrCheckin] = (),
        info: SrServerInfo = READ_ONLY_INFO,
        error: Exception | None = None,
    ) -> None:
        self._employees = tuple(employees)
        self._checkins = tuple(checkins)
        self._info = info
        self._error = error
        self.calls: list[tuple[date, date]] = []

    def fetch_employees(self) -> list[SrEmployee]:
        self._fail_if_broken()
        return list(self._employees)

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        self._fail_if_broken()
        self.calls.append((start, end))
        return [c for c in self._checkins if start <= c.at.date() <= end]

    def server_info(self) -> SrServerInfo:
        self._fail_if_broken()
        return self._info

    def _fail_if_broken(self) -> None:
        if self._error is not None:
            raise self._error
