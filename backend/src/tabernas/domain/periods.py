"""Date ranges, ISO weeks, months and the double-rest week parity."""

import calendar
from datetime import date, timedelta

from tabernas.domain.validation import DomainValidationError

MAX_RANGE_DAYS = 93


class RangeError(DomainValidationError):
    """Invalid or too-large date range."""


def validate_range(start: date, end: date) -> None:
    if end < start:
        raise RangeError("La fecha final es anterior a la inicial")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise RangeError(f"El rango máximo es de {MAX_RANGE_DAYS} días")


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


def iso_week_range(year: int, week: int) -> tuple[date, date]:
    monday = date.fromisocalendar(year, week, 1)
    return monday, monday + timedelta(days=6)


def validate_iso_week(year: int, week: int) -> None:
    try:
        date.fromisocalendar(year, week, 1)
    except ValueError as exc:
        raise RangeError(f"Semana ISO inválida: {year}-W{week:02d}") from exc


def month_range(year: int, month: int) -> tuple[date, date]:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last_day)


def iso_week_key(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def month_key(day: date) -> str:
    return f"{day.year}-{day.month:02d}"


def is_double_rest_week(anchor: date, day: date) -> bool:
    """True when `day` falls in a week with double rest, counting every 2 weeks from `anchor`."""
    weeks_from_anchor = (week_monday(day) - anchor).days // 7
    return weeks_from_anchor % 2 == 0
