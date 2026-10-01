"""Deterministic weekly-review findings (spec §4). The agent explains them, never creates them."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from datetime import date, timedelta

from tabernas.domain.periods import week_monday
from tabernas.domain.review_types import Finding, FindingKind, ReviewSettings
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, Planned, WarningCode

HISTORY_WEEKS = 4  # previous weeks that count for the repeated-lateness pattern

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
        *_repeated_lates(week, history, settings, start),
        *_config_warnings(warnings),
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


def _repeated_lates(
    week: Sequence[DayResult],
    history: Sequence[DayResult],
    settings: ReviewSettings,
    start: date,
) -> list[Finding]:
    since = start - timedelta(weeks=HISTORY_WEEKS)
    weeks_with_late: defaultdict[int, set[date]] = defaultdict(set)
    for r in [*history, *week]:
        if r.outcome == Outcome.LATE and r.day >= since:
            weeks_with_late[r.employee_id].add(week_monday(r.day))
    lates_this_week: defaultdict[int, list[DayResult]] = defaultdict(list)
    for r in week:
        if r.outcome == Outcome.LATE:
            lates_this_week[r.employee_id].append(r)
    candidates = (
        _late_finding(employee_id, lates, len(weeks_with_late[employee_id]), settings)
        for employee_id, lates in lates_this_week.items()
    )
    return [finding for finding in candidates if finding is not None]


def _late_finding(
    employee_id: int, lates: Sequence[DayResult], weeks_with_late: int, settings: ReviewSettings
) -> Finding | None:
    unjustified = sum(r.justification_id is None for r in lates)
    if unjustified < settings.late_week and weeks_with_late < settings.late_weeks:
        return None
    days = tuple(sorted(r.day for r in lates))
    return Finding(
        id=finding_id(FindingKind.REPEATED_LATE, employee_id, days[0]),
        kind=FindingKind.REPEATED_LATE,
        employee_id=employee_id,
        days=days,
        facts=(
            ("late_this_week", len(lates)),
            ("unjustified_this_week", unjustified),
            ("weeks_with_late", weeks_with_late),
        ),
    )


def _config_warnings(warnings: Iterable[AttendanceWarning]) -> list[Finding]:
    grouped: dict[tuple[WarningCode, int | None], list[AttendanceWarning]] = {}
    for warning in warnings:
        grouped.setdefault((warning.code, warning.employee_id), []).append(warning)
    return [
        _warning_finding(code, employee_id, items) for (code, employee_id), items in grouped.items()
    ]


def _warning_finding(
    code: WarningCode, employee_id: int | None, items: Sequence[AttendanceWarning]
) -> Finding:
    """`detail` is never copied: it may contain names (spec §4, Review Focus #2)."""
    days = tuple(sorted({w.day for w in items if w.day is not None}))
    kind_key = f"{FindingKind.CONFIG_WARNING}/{code.value}"
    return Finding(
        id=finding_id(kind_key, employee_id, days[0] if days else None),
        kind=FindingKind.CONFIG_WARNING,
        employee_id=employee_id,
        days=days,
        facts=(("code", code.value), ("occurrences", len(items))),
    )
