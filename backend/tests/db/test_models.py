from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow, RestRuleRow, ScheduleExceptionRow
from tabernas.domain.types import Area, ExceptionKind, RhType

DAY = date(2026, 9, 24)


def _employee(session: Session) -> EmployeeRow:
    row = EmployeeRow(
        short_name="EMPLEADO A", area=Area.OTHER, applies_lateness=True, tracks_attendance=True
    )
    session.add(row)
    session.flush()
    return row


def test_closure_cannot_have_employee(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.STORE_CLOSED, employee_id=employee.id, date_from=DAY, date_to=DAY
        )
    )
    with pytest.raises(IntegrityError, match="closure_has_no_employee"):
        session.flush()


def test_absence_requires_rh_type(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.WORK_TO_ABSENCE, employee_id=employee.id, date_from=DAY, date_to=DAY
        )
    )
    with pytest.raises(IntegrityError, match="absence_has_rh_type"):
        session.flush()


def test_absence_with_rh_type_is_valid(session: Session) -> None:
    employee = _employee(session)
    session.add(
        ScheduleExceptionRow(
            kind=ExceptionKind.WORK_TO_ABSENCE,
            employee_id=employee.id,
            date_from=DAY,
            date_to=DAY,
            rh_type=RhType.VACACIONES,
        )
    )
    session.flush()


def test_rest_rule_weekdays_must_differ(session: Session) -> None:
    employee = _employee(session)
    session.add(
        RestRuleRow(
            employee_id=employee.id,
            fixed_weekday=1,
            extra_weekday=1,
            double_rest_anchor=date(2026, 9, 28),
            valid_from=date(2026, 1, 1),
        )
    )
    with pytest.raises(IntegrityError, match="distinct_weekdays"):
        session.flush()
