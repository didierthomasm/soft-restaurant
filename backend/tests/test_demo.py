from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.demo import seed_demo_data
from tabernas.domain.types import Outcome, WarningCode
from tabernas.repos.employees import EmployeeRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.fake_source import FakeSource


def test_seed_is_idempotent(session: Session) -> None:
    assert len(seed_demo_data(session)) == 7
    assert seed_demo_data(session) == []
    manager = next(e for e in EmployeeRepo(session).find_all() if e.sr_id == 100)
    assert (manager.tracks_attendance, manager.applies_lateness) == (False, False)


def test_seeded_data_matches_fake_source(session: Session) -> None:
    seed_demo_data(session)
    today = date(2026, 9, 27)
    report = AttendanceService(
        session, FakeSource(today=lambda: today), lambda: datetime(2026, 9, 27, 20, 0)
    ).build(date(2026, 9, 1), today)
    codes = {w.code for w in report.warnings}
    assert WarningCode.NO_REST_RULE not in codes
    assert WarningCode.UNMAPPED_CHECKIN not in codes
    assert Outcome.LATE in {r.outcome for r in report.results}
