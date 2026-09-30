from datetime import date

from tabernas.domain.summary import EmployeeSummary, Grouping, summarize
from tabernas.domain.types import Outcome, RhType
from tests.domain.factories import result


def d(day: int, month: int = 9) -> date:
    return date(2026, month, day)


def test_weekly_summary_counts_every_outcome() -> None:
    results = [
        result(Outcome.OK, day=d(21)),
        result(Outcome.LATE, day=d(22)),
        result(Outcome.LATE, day=d(23), justification_id=1, rh_type=RhType.NO_CAPTURAR),
        result(Outcome.ABSENT, day=d(24)),
        result(Outcome.ABSENT, day=d(25), justification_id=2, rh_type=RhType.PERMISO),
        result(Outcome.JUSTIFIED, day=d(26), rh_type=RhType.VACACIONES),
        result(Outcome.UNREGISTERED_CHANGE, day=d(27)),
        result(Outcome.REST, employee_id=2, day=d(21)),
    ]
    assert summarize(results, Grouping.WEEK) == [
        EmployeeSummary(
            employee_id=1,
            period="2026-W39",
            worked=3,
            late=2,
            late_justified=1,
            absent=2,
            absent_justified=1,
            justified_by_type=((RhType.VACACIONES, 1),),
            unresolved=1,
        ),
        EmployeeSummary(2, "2026-W39", 0, 0, 0, 0, 0, (), 0),
    ]


def test_monthly_grouping_splits_at_month_boundary() -> None:
    results = [result(Outcome.OK, day=d(30)), result(Outcome.OK, day=d(1, 10))]
    assert [s.period for s in summarize(results, Grouping.MONTH)] == ["2026-09", "2026-10"]


def test_week_grouping_crosses_month_boundary() -> None:
    results = [result(Outcome.OK, day=d(30)), result(Outcome.OK, day=d(1, 10))]
    summaries = summarize(results, Grouping.WEEK)
    assert [(s.period, s.worked) for s in summaries] == [("2026-W40", 2)]
