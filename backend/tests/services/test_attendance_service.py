from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.domain.types import Employee, Incident, Outcome, RhType, WarningCode
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.source import SrCheckin
from tests.repos.helpers import make_employee
from tests.support import StubSource

WEEK_39 = (date(2026, 9, 21), date(2026, 9, 27))


def setup_employee(session: Session) -> Employee:
    employee = make_employee(session, 7, short_name="EMPLEADO G")
    RestRuleRepo(session).create(
        employee_id=employee.id,
        fixed_weekday=1,
        extra_weekday=0,
        double_rest_anchor=date(2026, 9, 28),
        valid_from=date(2026, 1, 1),
        valid_to=None,
    )
    return employee


def test_range_crossing_today_reads_sr_only_until_today(session: Session) -> None:
    # Review Focus #1
    setup_employee(session)
    source = StubSource()
    thursday_noon = datetime(2026, 9, 24, 12, 0)
    report = AttendanceService(session, source, lambda: thursday_noon).build(*WEEK_39)
    assert source.calls == [(date(2026, 9, 21), date(2026, 9, 24))]
    outcomes = {r.day.day: r.outcome for r in report.results}
    assert outcomes[24] == Outcome.PENDING
    assert {outcomes[25], outcomes[26], outcomes[27]} == {Outcome.FUTURE}


def test_future_range_does_not_call_sr(session: Session) -> None:
    setup_employee(session)
    source = StubSource()
    AttendanceService(session, source, lambda: datetime(2026, 9, 24, 12, 0)).build(
        date(2026, 10, 5), date(2026, 10, 11)
    )
    assert source.calls == []


def test_full_week_end_to_end(session: Session) -> None:
    employee = setup_employee(session)
    checkins = [
        SrCheckin(sr_id=7, at=datetime(2026, 9, 22, 16, 45)),  # Tuesday = rest day
        SrCheckin(sr_id=7, at=datetime(2026, 9, 23, 16, 51)),  # late by 11 minutes
        SrCheckin(sr_id=7, at=datetime(2026, 9, 24, 16, 40)),  # on time
    ]
    JustificationRepo(session).create(
        employee_id=employee.id,
        day=date(2026, 9, 21),
        incident=Incident.ABSENT,
        reason="Enfermo",
        rh_type=RhType.INCAPACIDAD,
    )
    report = AttendanceService(
        session, StubSource(checkins=checkins), lambda: datetime(2026, 9, 27, 20, 0)
    ).build(*WEEK_39)
    assert [r.outcome for r in report.results] == [
        Outcome.ABSENT,
        Outcome.UNREGISTERED_CHANGE,
        Outcome.LATE,
        Outcome.OK,
        Outcome.ABSENT,
        Outcome.ABSENT,
        Outcome.ABSENT,
    ]
    assert [(row.day.day, row.rh_type) for row in report.rh_rows] == [
        (21, RhType.INCAPACIDAD),
        (23, RhType.RETARDO),
        (25, RhType.FALTA_INJUSTIFICADA),
        (26, RhType.FALTA_INJUSTIFICADA),
        (27, RhType.FALTA_INJUSTIFICADA),
    ]
    assert [w.code for w in report.warnings] == [WarningCode.MISSING_RH_NAME]
