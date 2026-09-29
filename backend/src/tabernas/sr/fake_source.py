"""Synthetic SoftRestaurant for demos, E2E and CI. Deterministic; contains no real data."""

import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from tabernas.domain.periods import days, is_double_rest_week, validate_range
from tabernas.domain.types import DEFAULT_SETTINGS, Area
from tabernas.sr.source import SrCheckin, SrEmployee, SrServerInfo


@dataclass(frozen=True)
class FakeEmployee:
    sr_id: int
    name: str
    area: Area
    fixed_rest: int
    extra_rest: int
    checks_in: bool = True


FAKE_DOUBLE_REST_ANCHOR = date(2026, 9, 28)
FAKE_EMPLOYEES = (
    FakeEmployee(100, "GERENTE DEMO", Area.OTHER, fixed_rest=0, extra_rest=6, checks_in=False),
    FakeEmployee(101, "EMPLEADO A", Area.KITCHEN, fixed_rest=1, extra_rest=0),
    FakeEmployee(102, "EMPLEADO B", Area.KITCHEN, fixed_rest=6, extra_rest=0),
    FakeEmployee(103, "EMPLEADO C", Area.OTHER, fixed_rest=1, extra_rest=0),
    FakeEmployee(104, "EMPLEADO D", Area.OTHER, fixed_rest=6, extra_rest=0),
    FakeEmployee(105, "EMPLEADO E", Area.OTHER, fixed_rest=0, extra_rest=2),
    FakeEmployee(106, "EMPLEADO F", Area.OTHER, fixed_rest=1, extra_rest=0),
)
ABSENCE_RATE = 0.05
LATE_RATE = 0.15
REST_CHECKIN_RATE = 0.05


class FakeSource:
    def __init__(self, today: Callable[[], date] = date.today) -> None:
        self._today = today

    def fetch_employees(self) -> list[SrEmployee]:
        return [
            SrEmployee(sr_id=e.sr_id, name=e.name, kind=1, visible=True) for e in FAKE_EMPLOYEES
        ]

    def fetch_checkins(self, start: date, end: date) -> list[SrCheckin]:
        validate_range(start, end)
        last = min(end, self._today())
        return [
            checkin
            for day in days(start, last)
            for employee in FAKE_EMPLOYEES
            if employee.checks_in
            for checkin in _checkins_for(employee, day)
        ]

    def server_info(self) -> SrServerInfo:
        return SrServerInfo(
            server="FAKE",
            instance="FAKE",
            version="fake",
            edition="fake",
            database="fake",
            login="fake",
            is_datareader=True,
            is_denywriter=True,
            is_sysadmin=False,
        )


def is_fake_rest_day(employee: FakeEmployee, day: date) -> bool:
    weekday = day.weekday()
    if weekday == employee.fixed_rest:
        return True
    return weekday == employee.extra_rest and is_double_rest_week(FAKE_DOUBLE_REST_ANCHOR, day)


def _checkins_for(employee: FakeEmployee, day: date) -> list[SrCheckin]:
    rng = random.Random(f"{employee.sr_id}:{day.isoformat()}")
    roll = rng.random()
    if is_fake_rest_day(employee, day):
        if roll < REST_CHECKIN_RATE:
            return [_checkin(employee, day, rng.randint(-10, 5), rng)]
        return []
    if roll < ABSENCE_RATE:
        return []
    late = roll < ABSENCE_RATE + LATE_RATE
    offset = rng.randint(11, 40) if late else rng.randint(-25, 9)
    return [_checkin(employee, day, offset, rng)]


def _checkin(
    employee: FakeEmployee, day: date, offset_minutes: int, rng: random.Random
) -> SrCheckin:
    entry = datetime.combine(day, DEFAULT_SETTINGS.entry_time(employee.area))
    return SrCheckin(
        sr_id=employee.sr_id,
        at=entry + timedelta(minutes=offset_minutes, seconds=rng.randint(0, 59)),
    )
