from datetime import date

import pytest

from tabernas.domain.periods import (
    MAX_RANGE_DAYS,
    RangeError,
    days,
    is_double_rest_week,
    iso_week_key,
    iso_week_range,
    month_key,
    month_range,
    validate_iso_week,
    validate_range,
    week_monday,
)


def test_iso_week_39_of_2026_is_21_to_27_september() -> None:
    assert iso_week_range(2026, 39) == (date(2026, 9, 21), date(2026, 9, 27))


def test_month_range_handles_february() -> None:
    assert month_range(2026, 2) == (date(2026, 2, 1), date(2026, 2, 28))


def test_days_is_inclusive_and_empty_when_reversed() -> None:
    assert days(date(2026, 9, 21), date(2026, 9, 23)) == [
        date(2026, 9, 21),
        date(2026, 9, 22),
        date(2026, 9, 23),
    ]
    assert days(date(2026, 9, 23), date(2026, 9, 21)) == []


def test_week_monday() -> None:
    assert week_monday(date(2026, 9, 27)) == date(2026, 9, 21)
    assert week_monday(date(2026, 9, 21)) == date(2026, 9, 21)


def test_keys_use_iso_year_at_year_boundary() -> None:
    assert iso_week_key(date(2026, 9, 23)) == "2026-W39"
    assert iso_week_key(date(2027, 1, 1)) == "2026-W53"
    assert month_key(date(2027, 1, 1)) == "2027-01"


def test_validate_range_accepts_93_days() -> None:
    validate_range(date(2026, 7, 1), date(2026, 10, 1))  # 93 days inclusive


def test_validate_range_rejects_94_days_and_reversed() -> None:
    assert MAX_RANGE_DAYS == 93
    with pytest.raises(RangeError, match="93"):
        validate_range(date(2026, 7, 1), date(2026, 10, 2))
    with pytest.raises(RangeError, match="anterior"):
        validate_range(date(2026, 9, 2), date(2026, 9, 1))


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 9, 28), True),  # anchor week
        (date(2026, 10, 4), True),  # same week, Sunday
        (date(2026, 10, 5), False),  # next week
        (date(2026, 10, 12), True),  # two weeks later
        (date(2026, 9, 21), False),  # week before the anchor
        (date(2026, 9, 14), True),  # two weeks before the anchor
    ],
)
def test_double_rest_week_alternates_from_anchor(day: date, expected: bool) -> None:
    assert is_double_rest_week(date(2026, 9, 28), day) is expected


def test_validate_iso_week_accepts_week_53_only_in_long_years() -> None:
    validate_iso_week(2026, 53)  # 2026 starts on a Thursday: 53 ISO weeks
    with pytest.raises(RangeError, match="Semana ISO inválida"):
        validate_iso_week(2025, 53)
    with pytest.raises(RangeError, match="Semana ISO inválida"):
        validate_iso_week(2026, 0)
