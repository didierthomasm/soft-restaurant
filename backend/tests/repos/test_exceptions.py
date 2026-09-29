from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import ExceptionKind, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError
from tabernas.repos.exceptions import ExceptionRepo
from tests.repos.helpers import make_employee

DAY = date(2026, 9, 24)


def test_closure_has_no_employee_and_may_overlap_employee_exceptions(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.REST_TO_WORK,
        employee_id=employee.id,
        date_from=DAY,
        date_to=DAY,
        rh_type=None,
        comment="",
    )
    closure = repo.create(
        kind=ExceptionKind.STORE_CLOSED,
        employee_id=None,
        date_from=DAY,
        date_to=DAY,
        rh_type=None,
        comment="Ley Seca",
    )
    assert closure.employee_id is None
    assert len(repo.find_all(start=DAY, end=DAY)) == 2


def test_same_employee_overlap_conflicts(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.WORK_TO_ABSENCE,
        employee_id=employee.id,
        date_from=DAY,
        date_to=date(2026, 9, 26),
        rh_type=RhType.VACACIONES,
        comment="",
    )
    with pytest.raises(ConflictError, match="Ya hay una excepción"):
        repo.create(
            kind=ExceptionKind.PRESENT_NO_CHECKIN,
            employee_id=employee.id,
            date_from=date(2026, 9, 26),
            date_to=date(2026, 9, 26),
            rh_type=None,
            comment="",
        )


def test_find_all_returns_exceptions_overlapping_the_range(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    repo.create(
        kind=ExceptionKind.WORK_TO_ABSENCE,
        employee_id=employee.id,
        date_from=date(2026, 9, 18),
        date_to=date(2026, 9, 22),
        rh_type=RhType.INCAPACIDAD,
        comment="",
    )
    assert len(repo.find_all(start=date(2026, 9, 21), end=date(2026, 9, 27))) == 1
    assert repo.find_all(start=date(2026, 9, 23), end=date(2026, 9, 27)) == []


def test_update_dates_and_reject_kind_change(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    created = repo.create(
        kind=ExceptionKind.REST_TO_WORK,
        employee_id=employee.id,
        date_from=DAY,
        date_to=DAY,
        rh_type=None,
        comment="",
    )
    moved = repo.update(created.id, {"date_from": date(2026, 9, 25), "date_to": date(2026, 9, 25)})
    assert moved.date_from == date(2026, 9, 25)
    with pytest.raises(DomainValidationError, match="kind"):
        repo.update(created.id, {"kind": ExceptionKind.STORE_CLOSED})


def test_rest_swap_creates_absence_and_extra_workday(session: Session) -> None:
    employee = make_employee(session)
    absence, worked = ExceptionRepo(session).create_rest_swap(
        employee_id=employee.id,
        absent_day=date(2026, 9, 23),
        worked_day=date(2026, 9, 29),
        comment="Cambio de descanso",
    )
    assert (absence.kind, absence.rh_type, absence.date_from) == (
        ExceptionKind.WORK_TO_ABSENCE,
        RhType.DESCANSO,
        date(2026, 9, 23),
    )
    assert (worked.kind, worked.rh_type, worked.date_from) == (
        ExceptionKind.REST_TO_WORK,
        None,
        date(2026, 9, 29),
    )


def test_rest_swap_is_atomic(session: Session) -> None:
    employee = make_employee(session)
    repo = ExceptionRepo(session)
    existing = repo.create(
        kind=ExceptionKind.PRESENT_NO_CHECKIN,
        employee_id=employee.id,
        date_from=date(2026, 9, 29),
        date_to=date(2026, 9, 29),
        rh_type=None,
        comment="",
    )
    with pytest.raises(ConflictError):
        repo.create_rest_swap(
            employee_id=employee.id,
            absent_day=date(2026, 9, 23),
            worked_day=date(2026, 9, 29),
            comment="",
        )
    assert repo.find_all() == [existing]


def test_rest_swap_needs_two_different_days(session: Session) -> None:
    employee = make_employee(session)
    with pytest.raises(DomainValidationError, match="distintos"):
        ExceptionRepo(session).create_rest_swap(
            employee_id=employee.id, absent_day=DAY, worked_day=DAY, comment=""
        )
