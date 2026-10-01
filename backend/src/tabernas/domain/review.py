"""Deterministic weekly-review findings (spec §4). The agent explains them, never creates them."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date

from tabernas.domain.review_types import Finding, FindingKind, ReviewSettings
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, Planned

KIND_ORDER = {kind: index for index, kind in enumerate(FindingKind)}


def finding_id(kind: str, employee_id: int | None, first_day: date | None) -> str:
    employee = "-" if employee_id is None else str(employee_id)
    day = "-" if first_day is None else first_day.isoformat()
    return f"{kind}:{employee}:{day}"


def find_findings(
    week_results: Sequence[DayResult],
    history_results: Sequence[DayResult],
    warnings: Sequence[AttendanceWarning],
    settings: ReviewSettings,
    start: date,
    end: date,
) -> list[Finding]:
    week = [r for r in week_results if start <= r.day <= end]
    history = [r for r in history_results if r.day < start]
    streaks = _streaks([*history, *week], settings.streak_days, start, end)
    in_streak = {(f.employee_id, day) for f in streaks for day in f.days}
    findings = [
        *_rest_day_checkins(week),
        *_absences(week, in_streak),
        *streaks,
    ]
    return sorted(findings, key=_sort_key)


def _sort_key(finding: Finding) -> tuple[int, int, date, str]:
    return (
        KIND_ORDER[finding.kind],
        -1 if finding.employee_id is None else finding.employee_id,
        finding.days[0] if finding.days else date.min,
        finding.id,
    )


def _is_open_absence(result: DayResult) -> bool:
    return result.outcome == Outcome.ABSENT and result.justification_id is None


def _rest_day_checkins(week: Iterable[DayResult]) -> list[Finding]:
    return [
        Finding(
            id=finding_id(FindingKind.REST_DAY_CHECKIN, r.employee_id, r.day),
            kind=FindingKind.REST_DAY_CHECKIN,
            employee_id=r.employee_id,
            days=(r.day,),
            facts=(("checkin_time", r.checkin.strftime("%H:%M")),) if r.checkin else (),
        )
        for r in week
        if r.outcome == Outcome.UNREGISTERED_CHANGE
    ]


def _absences(week: Iterable[DayResult], in_streak: set[tuple[int | None, date]]) -> list[Finding]:
    return [
        Finding(
            id=finding_id(FindingKind.ABSENT_NO_EXCEPTION, r.employee_id, r.day),
            kind=FindingKind.ABSENT_NO_EXCEPTION,
            employee_id=r.employee_id,
            days=(r.day,),
        )
        for r in week
        if _is_open_absence(r) and (r.employee_id, r.day) not in in_streak
    ]


def _streaks(results: Sequence[DayResult], min_days: int, start: date, end: date) -> list[Finding]:
    work_days: defaultdict[int, list[DayResult]] = defaultdict(list)
    for r in sorted(results, key=lambda item: (item.employee_id, item.day)):
        if r.planned == Planned.WORK:
            work_days[r.employee_id].append(r)
    return [
        Finding(
            id=finding_id(FindingKind.NO_CHECKIN_STREAK, employee_id, run[0]),
            kind=FindingKind.NO_CHECKIN_STREAK,
            employee_id=employee_id,
            days=run,
            facts=(("days", len(run)),),
        )
        for employee_id, days in work_days.items()
        for run in _absence_runs(days)
        if len(run) >= min_days and start <= run[-1] <= end
    ]


def _absence_runs(work_days: Sequence[DayResult]) -> list[tuple[date, ...]]:
    """Maximal runs of consecutive unjustified absences among an employee's work days."""
    runs: list[tuple[date, ...]] = []
    current: tuple[date, ...] = ()
    for r in work_days:
        if _is_open_absence(r):
            current = (*current, r.day)
            continue
        if current:
            runs.append(current)
        current = ()
    if current:
        runs.append(current)
    return runs
