"""Planned calendar: what each employee should do each day, before looking at check-ins."""

from collections.abc import Sequence
from datetime import date

from tabernas.domain.periods import days, is_double_rest_week, validate_range
from tabernas.domain.types import (
    AttendanceWarning,
    Employee,
    ExceptionKind,
    Planned,
    PlannedDay,
    RestRule,
    ScheduleException,
    WarningCode,
)


def covers(exception: ScheduleException, day: date) -> bool:
    return exception.date_from <= day <= exception.date_to


def rule_for(rules: Sequence[RestRule], day: date) -> RestRule | None:
    return next(
        (r for r in rules if r.valid_from <= day and (r.valid_to is None or day <= r.valid_to)),
        None,
    )


def planned_by_rule(rule: RestRule | None, day: date) -> Planned:
    if rule is None:
        return Planned.WORK
    weekday = day.weekday()
    if weekday == rule.fixed_weekday:
        return Planned.REST
    if weekday == rule.extra_weekday and is_double_rest_week(rule.double_rest_anchor, day):
        return Planned.REST
    return Planned.WORK


def planned_calendar(
    employees: Sequence[Employee],
    rules: Sequence[RestRule],
    exceptions: Sequence[ScheduleException],
    start: date,
    end: date,
) -> tuple[list[PlannedDay], list[AttendanceWarning]]:
    validate_range(start, end)
    period = days(start, end)
    closures = [e for e in exceptions if e.kind == ExceptionKind.STORE_CLOSED]
    active = sorted((e for e in employees if e.active), key=lambda e: e.id)
    planned: list[PlannedDay] = []
    warnings: list[AttendanceWarning] = []
    for employee in active:
        own_rules = [r for r in rules if r.employee_id == employee.id]
        own_exceptions = [e for e in exceptions if e.employee_id == employee.id]
        planned.extend(
            _plan_day(employee.id, day, own_rules, own_exceptions, closures) for day in period
        )
        missing = next((day for day in period if rule_for(own_rules, day) is None), None)
        if missing is not None:
            warnings.append(
                AttendanceWarning(
                    WarningCode.NO_REST_RULE, employee.id, missing, "Sin regla de descanso vigente"
                )
            )
    return planned, warnings


def _find(exceptions: Sequence[ScheduleException], kind: ExceptionKind) -> ScheduleException | None:
    return next((e for e in exceptions if e.kind == kind), None)


def _plan_day(
    employee_id: int,
    day: date,
    rules: Sequence[RestRule],
    exceptions: Sequence[ScheduleException],
    closures: Sequence[ScheduleException],
) -> PlannedDay:
    closure = next((c for c in closures if covers(c, day)), None)
    if closure is not None:
        return PlannedDay(employee_id, day, Planned.CLOSED, comment=closure.comment)
    covering = [e for e in exceptions if covers(e, day)]
    present = _find(covering, ExceptionKind.PRESENT_NO_CHECKIN)
    absence = _find(covering, ExceptionKind.WORK_TO_ABSENCE)
    if absence is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.ABSENCE,
            rh_type=absence.rh_type,
            comment=absence.comment,
            exception=absence,
        )
    manual = _find(covering, ExceptionKind.MANUAL_ABSENCE)
    if manual is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.WORK,
            manual_absence=True,
            comment=manual.comment,
            exception=manual,
        )
    extra_work = _find(covering, ExceptionKind.REST_TO_WORK)
    if extra_work is not None:
        return PlannedDay(
            employee_id,
            day,
            Planned.WORK,
            present_no_checkin=present is not None,
            comment=extra_work.comment,
            exception=extra_work,
        )
    return PlannedDay(
        employee_id,
        day,
        planned_by_rule(rule_for(rules, day), day),
        present_no_checkin=present is not None,
        exception=present,
    )
