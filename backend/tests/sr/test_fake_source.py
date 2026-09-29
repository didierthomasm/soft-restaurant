from datetime import date, datetime, timedelta

import pytest

from tabernas.domain.periods import RangeError, days
from tabernas.domain.types import DEFAULT_SETTINGS
from tabernas.sr.fake_source import FAKE_EMPLOYEES, FakeSource, is_fake_rest_day

TODAY = date(2026, 9, 27)
START = date(2026, 7, 1)


def source() -> FakeSource:
    return FakeSource(today=lambda: TODAY)


def test_is_deterministic() -> None:
    first = source().fetch_checkins(START, TODAY)
    assert first
    assert first == source().fetch_checkins(START, TODAY)


def test_never_returns_future_checkins() -> None:
    checkins = source().fetch_checkins(date(2026, 9, 21), date(2026, 10, 4))
    assert max(c.at.date() for c in checkins) <= TODAY
    assert source().fetch_checkins(date(2026, 10, 1), date(2026, 10, 7)) == []


def test_manager_never_checks_in() -> None:
    assert all(c.sr_id != 100 for c in source().fetch_checkins(START, TODAY))


def test_produces_late_absent_and_rest_day_checkins() -> None:
    checkins = source().fetch_checkins(START, TODAY)
    by_key = {(c.sr_id, c.at.date()): c.at for c in checkins}
    checking = [e for e in FAKE_EMPLOYEES if e.checks_in]
    late = absent = on_rest = 0
    for employee in checking:
        entry = DEFAULT_SETTINGS.entry_time(employee.area)
        for day in days(START, TODAY):
            at = by_key.get((employee.sr_id, day))
            if is_fake_rest_day(employee, day):
                on_rest += at is not None
            elif at is None:
                absent += 1
            elif at.replace(second=0) > datetime.combine(day, entry) + timedelta(minutes=10):
                late += 1
    assert late > 0 and absent > 0 and on_rest > 0


def test_range_is_validated() -> None:
    with pytest.raises(RangeError):
        source().fetch_checkins(date(2026, 1, 1), date(2026, 6, 1))


def test_employees_include_manager_and_six_checking_employees() -> None:
    employees = source().fetch_employees()
    assert [e.sr_id for e in employees] == [100, 101, 102, 103, 104, 105, 106]
    assert all(e.name.isupper() for e in employees)


def test_server_info_is_read_only() -> None:
    assert source().server_info().read_only
