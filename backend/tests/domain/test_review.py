from collections.abc import Sequence
from dataclasses import replace
from datetime import date, datetime, timedelta

from tabernas.domain.review import find_findings, finding_id
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    Finding,
    FindingKind,
    ReviewSettings,
)
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome
from tests.domain.factories import WEEK_39, result

START, END = WEEK_39
MON, TUE, WED, THU, FRI, SAT, SUN = (START + timedelta(days=offset) for offset in range(7))
PREV_SAT, PREV_SUN = date(2026, 9, 19), date(2026, 9, 20)


def find(
    week: Sequence[DayResult] = (),
    history: Sequence[DayResult] = (),
    warnings: Sequence[AttendanceWarning] = (),
    settings: ReviewSettings = DEFAULT_REVIEW_SETTINGS,
) -> list[Finding]:
    return find_findings(list(week), list(history), list(warnings), settings, START, END)


def kinds(findings: Sequence[Finding]) -> list[FindingKind]:
    return [f.kind for f in findings]


def test_finding_id_format() -> None:
    assert finding_id(FindingKind.REPEATED_LATE, 4, WED) == "REPEATED_LATE:4:2026-09-23"
    assert finding_id("CONFIG_WARNING/UNMAPPED_CHECKIN", None, None) == (
        "CONFIG_WARNING/UNMAPPED_CHECKIN:-:-"
    )


def test_clean_week_has_no_findings() -> None:
    assert find([result(Outcome.OK, day=d) for d in (MON, WED, THU)]) == []


def test_rest_day_checkin_reports_the_time() -> None:
    checkin = replace(
        result(Outcome.UNREGISTERED_CHANGE, day=TUE), checkin=datetime(2026, 9, 22, 16, 45, 30)
    )
    assert find([checkin]) == [
        Finding(
            id="REST_DAY_CHECKIN:1:2026-09-22",
            kind=FindingKind.REST_DAY_CHECKIN,
            employee_id=1,
            days=(TUE,),
            facts=(("checkin_time", "16:45"),),
        )
    ]


def test_single_unjustified_absence() -> None:
    assert find([result(Outcome.ABSENT, day=WED)]) == [
        Finding(
            id="ABSENT_NO_EXCEPTION:1:2026-09-23",
            kind=FindingKind.ABSENT_NO_EXCEPTION,
            employee_id=1,
            days=(WED,),
        )
    ]


def test_justified_absence_is_not_a_finding() -> None:
    assert find([result(Outcome.ABSENT, day=WED, justification_id=3)]) == []


def test_two_consecutive_absences_are_one_streak() -> None:
    findings = find([result(Outcome.ABSENT, day=WED), result(Outcome.ABSENT, day=THU)])
    assert findings == [
        Finding(
            id="NO_CHECKIN_STREAK:1:2026-09-23",
            kind=FindingKind.NO_CHECKIN_STREAK,
            employee_id=1,
            days=(WED, THU),
            facts=(("days", 2),),
        )
    ]


def test_rest_day_in_the_middle_does_not_break_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.REST, day=TUE),
        result(Outcome.ABSENT, day=WED),
    ]
    findings = find(week)
    assert kinds(findings) == [FindingKind.NO_CHECKIN_STREAK]
    assert findings[0].days == (MON, WED)


def test_worked_day_breaks_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.OK, day=TUE),
        result(Outcome.ABSENT, day=WED),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_justified_absence_breaks_a_streak() -> None:
    week = [
        result(Outcome.ABSENT, day=MON),
        result(Outcome.ABSENT, day=TUE, justification_id=9),
        result(Outcome.ABSENT, day=WED),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_streak_can_start_in_the_previous_week() -> None:
    findings = find(
        week=[result(Outcome.ABSENT, day=MON), result(Outcome.OK, day=TUE)],
        history=[result(Outcome.ABSENT, day=PREV_SUN)],
    )
    assert [(f.id, f.days) for f in findings] == [
        ("NO_CHECKIN_STREAK:1:2026-09-20", (PREV_SUN, MON))
    ]


def test_streak_that_ended_last_week_is_not_reported() -> None:
    findings = find(
        week=[result(Outcome.OK, day=MON)],
        history=[result(Outcome.ABSENT, day=PREV_SAT), result(Outcome.ABSENT, day=PREV_SUN)],
    )
    assert findings == []


def test_pending_and_future_days_end_a_streak_and_are_ignored() -> None:
    week = [
        result(Outcome.ABSENT, day=WED),
        result(Outcome.PENDING, day=THU),
        result(Outcome.FUTURE, day=FRI),
    ]
    assert kinds(find(week)) == [FindingKind.ABSENT_NO_EXCEPTION]


def test_streak_length_comes_from_settings() -> None:
    week = [result(Outcome.ABSENT, day=WED), result(Outcome.ABSENT, day=THU)]
    findings = find(week, settings=ReviewSettings(streak_days=3))
    assert kinds(findings) == [FindingKind.ABSENT_NO_EXCEPTION] * 2


def test_findings_are_ordered_and_ids_are_stable() -> None:
    week = [
        result(Outcome.ABSENT, employee_id=2, day=MON),
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=3, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 45),
        ),
        result(Outcome.ABSENT, employee_id=1, day=WED),
        result(Outcome.ABSENT, employee_id=1, day=THU),
    ]
    first = find(week)
    assert [f.id for f in first] == [
        "REST_DAY_CHECKIN:3:2026-09-22",
        "ABSENT_NO_EXCEPTION:2:2026-09-21",
        "NO_CHECKIN_STREAK:1:2026-09-23",
    ]
    assert find(list(reversed(week))) == first
