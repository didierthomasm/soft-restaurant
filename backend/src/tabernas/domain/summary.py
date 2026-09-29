"""Per-employee totals by ISO week or month."""

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from tabernas.domain.periods import iso_week_key, month_key
from tabernas.domain.types import DayResult, Outcome, RhType


class Grouping(StrEnum):
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True)
class EmployeeSummary:
    employee_id: int
    period: str
    worked: int
    late: int
    late_justified: int
    absent: int
    absent_justified: int
    justified_by_type: tuple[tuple[RhType, int], ...]
    unresolved: int


def period_key(day: date, grouping: Grouping) -> str:
    return iso_week_key(day) if grouping == Grouping.WEEK else month_key(day)


def summarize(results: Sequence[DayResult], grouping: Grouping) -> list[EmployeeSummary]:
    groups: defaultdict[tuple[int, str], list[DayResult]] = defaultdict(list)
    for r in results:
        groups[(r.employee_id, period_key(r.day, grouping))].append(r)
    return [
        _summarize_group(employee_id, period, group)
        for (employee_id, period), group in sorted(groups.items())
    ]


def _summarize_group(
    employee_id: int, period: str, results: Sequence[DayResult]
) -> EmployeeSummary:
    late = [r for r in results if r.outcome == Outcome.LATE]
    absent = [r for r in results if r.outcome == Outcome.ABSENT]
    by_type = Counter(
        r.rh_type for r in results if r.outcome == Outcome.JUSTIFIED and r.rh_type is not None
    )
    return EmployeeSummary(
        employee_id=employee_id,
        period=period,
        worked=sum(r.outcome in (Outcome.OK, Outcome.LATE) for r in results),
        late=len(late),
        late_justified=sum(r.justification_id is not None for r in late),
        absent=len(absent),
        absent_justified=sum(r.justification_id is not None for r in absent),
        justified_by_type=tuple(sorted(by_type.items())),
        unresolved=sum(r.outcome == Outcome.UNREGISTERED_CHANGE for r in results),
    )
