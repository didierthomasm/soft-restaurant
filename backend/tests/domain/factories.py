"""Synthetic domain objects for tests. Reference week: 2026-W39 (Mon 21 – Sun 27 Sep)."""

from datetime import date

from tabernas.domain.types import (
    Area,
    Employee,
    ExceptionKind,
    Planned,
    PlannedDay,
    RestRule,
    RhType,
    ScheduleException,
)

WEEK_39 = (date(2026, 9, 21), date(2026, 9, 27))
ANCHOR = date(2026, 9, 28)  # Monday, double-rest week


def employee(
    id: int = 1,
    *,
    area: Area = Area.OTHER,
    applies_lateness: bool = True,
    tracks_attendance: bool = True,
    active: bool = True,
    rh_name: str | None = "EMPLEADO RH",
) -> Employee:
    return Employee(
        id=id,
        sr_id=id + 100,
        short_name=f"E{id}",
        rh_name=rh_name,
        area=area,
        applies_lateness=applies_lateness,
        tracks_attendance=tracks_attendance,
        active=active,
    )


def rule(
    employee_id: int = 1,
    *,
    fixed: int = 1,  # Tuesday
    extra: int = 0,  # Monday
    anchor: date = ANCHOR,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    id: int = 1,
) -> RestRule:
    return RestRule(
        id=id,
        employee_id=employee_id,
        fixed_weekday=fixed,
        extra_weekday=extra,
        double_rest_anchor=anchor,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def exception(
    kind: ExceptionKind,
    day: date,
    *,
    until: date | None = None,
    employee_id: int | None = 1,
    rh_type: RhType | None = None,
    comment: str = "",
    id: int = 1,
) -> ScheduleException:
    return ScheduleException(
        id=id,
        kind=kind,
        employee_id=None if kind == ExceptionKind.STORE_CLOSED else employee_id,
        date_from=day,
        date_to=until or day,
        rh_type=rh_type,
        comment=comment,
    )


def planned(
    day: date,
    kind: Planned = Planned.WORK,
    *,
    employee_id: int = 1,
    rh_type: RhType | None = None,
    present_no_checkin: bool = False,
    manual_absence: bool = False,
) -> PlannedDay:
    return PlannedDay(
        employee_id=employee_id,
        day=day,
        planned=kind,
        rh_type=rh_type,
        present_no_checkin=present_no_checkin,
        manual_absence=manual_absence,
    )
