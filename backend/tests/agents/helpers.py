"""Synthetic employees and review contexts for agent tests. No real data."""

from collections.abc import Sequence
from datetime import date, datetime

from tabernas.domain.review import find_findings
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    ReviewContext,
    ReviewSettings,
    proposed_rows,
)
from tabernas.domain.rh import to_rh_rows
from tabernas.domain.types import Area, AttendanceWarning, DayResult, Employee

WEEK_START, WEEK_END = date(2026, 9, 21), date(2026, 9, 27)  # 2026-W39
AS_OF = datetime(2026, 9, 24, 17, 30)


def person(employee_id: int, short_name: str, rh_name: str | None = None) -> Employee:
    return Employee(
        id=employee_id,
        sr_id=100 + employee_id,
        short_name=short_name,
        rh_name=rh_name,
        area=Area.OTHER,
        applies_lateness=True,
        tracks_attendance=True,
        active=True,
    )


ANA = person(1, "ANA PRUEBA", "ANA PRUEBA LOPEZ")
BETO = person(2, "BETO PRUEBA", "ALBERTO PRUEBA RUIZ")
STAFF = (ANA, BETO)


def make_context(
    week: Sequence[DayResult] = (),
    history: Sequence[DayResult] = (),
    warnings: Sequence[AttendanceWarning] = (),
    employees: Sequence[Employee] = STAFF,
    settings: ReviewSettings = DEFAULT_REVIEW_SETTINGS,
) -> ReviewContext:
    findings = find_findings(
        list(week), list(history), list(warnings), settings, WEEK_START, WEEK_END
    )
    rows, _ = to_rh_rows(list(week), list(employees))
    return ReviewContext(
        iso_year=2026,
        iso_week=39,
        start=WEEK_START,
        end=WEEK_END,
        as_of=AS_OF,
        employees=tuple(employees),
        week_results=tuple(week),
        history_results=tuple(history),
        rh_rows=proposed_rows(rows),
        findings=tuple(findings),
    )
