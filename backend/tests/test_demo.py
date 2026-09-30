from datetime import date, datetime

import pytest
from sqlalchemy.orm import Session

from tabernas.demo import seed_demo_data
from tabernas.domain.types import Area, Outcome, WarningCode
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.fake_source import FakeSource


def test_seed_is_idempotent(session: Session) -> None:
    assert len(seed_demo_data(session)) == 7
    assert seed_demo_data(session) == []
    manager = next(e for e in EmployeeRepo(session).find_all() if e.sr_id == 100)
    assert (manager.tracks_attendance, manager.applies_lateness) == (False, False)


def test_seed_refuses_when_a_real_employee_exists(session: Session) -> None:
    employees = EmployeeRepo(session)
    employees.create(
        sr_id=999,
        short_name="EMPLEADO REAL",
        rh_name="Empleado Real",
        area=Area.OTHER,
        applies_lateness=True,
        tracks_attendance=True,
    )
    with pytest.raises(DomainValidationError, match="empleados reales"):
        seed_demo_data(session)
    assert employees.find_all() == [employees.find_all()[0]]


def test_seed_refuses_when_a_real_employee_has_no_sr_id(session: Session) -> None:
    employees = EmployeeRepo(session)
    employees.create(
        sr_id=None,
        short_name="EMPLEADO SIN SR",
        rh_name="Empleado Sin SR",
        area=Area.OTHER,
        applies_lateness=False,
        tracks_attendance=False,
    )
    with pytest.raises(DomainValidationError, match="empleados reales"):
        seed_demo_data(session)
    assert len(employees.find_all()) == 1


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
