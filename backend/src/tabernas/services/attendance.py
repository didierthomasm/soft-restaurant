"""Builds attendance reports. The only place that joins Postgres config, SR and the domain."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.orm import Session

from tabernas.domain.compare import compare
from tabernas.domain.justify import apply_justifications
from tabernas.domain.periods import validate_range
from tabernas.domain.planning import planned_calendar
from tabernas.domain.rh import to_rh_rows
from tabernas.domain.types import AttendanceWarning, Checkin, DayResult, Employee, RhRow
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.exceptions import ExceptionRepo
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.repos.settings import SettingsRepo
from tabernas.sr.source import SrSource


@dataclass(frozen=True)
class AttendanceReport:
    start: date
    end: date
    employees: tuple[Employee, ...]
    results: tuple[DayResult, ...]
    rh_rows: tuple[RhRow, ...]
    warnings: tuple[AttendanceWarning, ...]


class AttendanceService:
    def __init__(self, session: Session, source: SrSource, clock: Callable[[], datetime]) -> None:
        self._session = session
        self._source = source
        self._clock = clock

    def build(self, start: date, end: date) -> AttendanceReport:
        validate_range(start, end)
        now = self._clock()
        today = now.date()
        employees = EmployeeRepo(self._session).find_all()
        planned, plan_warnings = planned_calendar(
            employees,
            RestRuleRepo(self._session).find_all(),
            ExceptionRepo(self._session).find_all(start=start, end=end),
            start,
            end,
        )
        compared, compare_warnings = compare(
            planned,
            employees,
            self._checkins(start, end, today),
            SettingsRepo(self._session).get(),
            today,
            now,
        )
        results, justify_warnings = apply_justifications(
            compared, JustificationRepo(self._session).find_all(start=start, end=end)
        )
        rows, rh_warnings = to_rh_rows(results, employees)
        return AttendanceReport(
            start=start,
            end=end,
            employees=tuple(e for e in employees if e.active),  # repo orders by name
            results=tuple(results),
            rh_rows=tuple(rows),
            warnings=(*plan_warnings, *compare_warnings, *justify_warnings, *rh_warnings),
        )

    def _checkins(self, start: date, end: date, today: date) -> list[Checkin]:
        if start > today:
            return []
        fetched = self._source.fetch_checkins(start, min(end, today))
        return [Checkin(sr_id=c.sr_id, at=c.at) for c in fetched]
