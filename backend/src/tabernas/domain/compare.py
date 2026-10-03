"""Planned vs actual: turns planned days + SR check-ins into per-day outcomes."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime, time, timedelta

from tabernas.domain.types import (
    AttendanceSettings,
    AttendanceWarning,
    Checkin,
    DayResult,
    Employee,
    Outcome,
    Planned,
    PlannedDay,
    WarningCode,
)

FirstCheckins = Mapping[tuple[int, date], datetime]


def first_checkins(checkins: Sequence[Checkin]) -> dict[tuple[int, date], datetime]:
    """Earliest check-in per (sr_id, calendar day)."""
    firsts: dict[tuple[int, date], datetime] = {}
    for item in sorted(checkins, key=lambda c: c.at, reverse=True):
        firsts[(item.sr_id, item.at.date())] = item.at
    return firsts


def truncate_to_minute(value: datetime) -> datetime:
    return value.replace(second=0, microsecond=0)


def entry_limit(day: date, entry: time, tolerance_minutes: int) -> datetime:
    return datetime.combine(day, entry) + timedelta(minutes=tolerance_minutes)


def compare(
    planned: Sequence[PlannedDay],
    employees: Sequence[Employee],
    checkins: Sequence[Checkin],
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> tuple[list[DayResult], list[AttendanceWarning]]:
    by_id = {e.id: e for e in employees}
    firsts = first_checkins(checkins)
    results = [
        _evaluate(day_plan, by_id[day_plan.employee_id], firsts, settings, today, now)
        for day_plan in planned
    ]
    warnings = _unmapped_warnings(firsts, planned, by_id) + _no_sr_id_warnings(planned, by_id)
    return results, warnings


def _evaluate(
    day_plan: PlannedDay,
    employee: Employee,
    firsts: FirstCheckins,
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> DayResult:
    checkin = None if employee.sr_id is None else firsts.get((employee.sr_id, day_plan.day))
    base = DayResult(
        employee_id=day_plan.employee_id,
        day=day_plan.day,
        planned=day_plan.planned,
        outcome=Outcome.OK,
        checkin=checkin,
        rh_type=day_plan.rh_type,
        comment=day_plan.comment,
        exception=day_plan.exception,
    )
    if day_plan.day > today:
        return replace(base, outcome=Outcome.FUTURE)
    if day_plan.planned == Planned.CLOSED:
        return replace(base, outcome=Outcome.CLOSED)
    if day_plan.planned == Planned.ABSENCE:
        return replace(base, outcome=Outcome.JUSTIFIED)
    if day_plan.planned == Planned.REST:
        outcome = Outcome.UNREGISTERED_CHANGE if checkin else Outcome.REST
        return replace(base, outcome=outcome)
    return _evaluate_work(base, day_plan, employee, settings, today, now)


def _evaluate_work(
    base: DayResult,
    day_plan: PlannedDay,
    employee: Employee,
    settings: AttendanceSettings,
    today: date,
    now: datetime,
) -> DayResult:
    if day_plan.manual_absence:
        return replace(base, outcome=Outcome.ABSENT)
    if not employee.tracks_attendance:
        return base
    entry = settings.entry_time(employee.area)
    limit = entry_limit(day_plan.day, entry, settings.tolerance_minutes)
    if base.checkin is not None:
        arrived = truncate_to_minute(base.checkin)
        if employee.applies_lateness and arrived > limit:
            minutes = int((arrived - datetime.combine(day_plan.day, entry)).total_seconds() // 60)
            return replace(base, outcome=Outcome.LATE, minutes_late=minutes)
        return base
    if day_plan.present_no_checkin:
        return base
    if day_plan.day == today and truncate_to_minute(now) <= limit:
        return replace(base, outcome=Outcome.PENDING)
    return replace(base, outcome=Outcome.ABSENT)


def _unmapped_warnings(
    firsts: FirstCheckins, planned: Sequence[PlannedDay], by_id: Mapping[int, Employee]
) -> list[AttendanceWarning]:
    mapped = {by_id[p.employee_id].sr_id for p in planned} - {None}
    return [
        AttendanceWarning(
            WarningCode.UNMAPPED_CHECKIN,
            None,
            day,
            f"Checada del id SR {sr_id} sin empleado activo configurado",
        )
        for sr_id, day in sorted(firsts)
        if sr_id not in mapped
    ]


def _no_sr_id_warnings(
    planned: Sequence[PlannedDay], by_id: Mapping[int, Employee]
) -> list[AttendanceWarning]:
    """One warning per employee that tracks attendance but has no SR id (every workday
    would otherwise silently come out as an unexplained absence)."""
    first_day: dict[int, date] = {}
    for day_plan in planned:
        employee = by_id[day_plan.employee_id]
        if employee.sr_id is not None or not employee.tracks_attendance:
            continue
        current = first_day.get(employee.id)
        if current is None or day_plan.day < current:
            first_day[employee.id] = day_plan.day
    return [
        AttendanceWarning(
            WarningCode.NO_SR_ID,
            employee_id,
            day,
            f"{by_id[employee_id].short_name} no tiene id de SR; sus días salen como falta",
        )
        for employee_id, day in sorted(first_day.items())
    ]
