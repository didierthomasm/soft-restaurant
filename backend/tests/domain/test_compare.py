from dataclasses import replace
from datetime import date, datetime, time

from tabernas.domain.compare import compare
from tabernas.domain.types import (
    DEFAULT_SETTINGS,
    Area,
    Checkin,
    DayResult,
    Employee,
    ExceptionKind,
    Outcome,
    Planned,
    PlannedDay,
    RhType,
    WarningCode,
)
from tests.domain.factories import employee, exception, planned

DAY = date(2026, 9, 23)  # Wednesday
EVENING = datetime(2026, 9, 27, 20, 0)


def at(hour: int, minute: int, second: int = 0, day: date = DAY) -> datetime:
    return datetime.combine(day, time(hour, minute, second))


def checkin(
    hour: int, minute: int, second: int = 0, *, sr_id: int = 101, day: date = DAY
) -> Checkin:
    return Checkin(sr_id=sr_id, at=at(hour, minute, second, day))


def run_one(
    day_plan: PlannedDay,
    checkins: list[Checkin],
    emp: Employee | None = None,
    *,
    today: date = date(2026, 9, 27),
    now: datetime = EVENING,
) -> DayResult:
    results, _ = compare([day_plan], [emp or employee()], checkins, DEFAULT_SETTINGS, today, now)
    return results[0]


def test_on_time_until_last_second_of_tolerance() -> None:
    result = run_one(planned(DAY), [checkin(16, 50, 59)])
    assert (result.outcome, result.checkin) == (Outcome.OK, at(16, 50, 59))


def test_late_from_next_minute_counts_minutes_from_entry_time() -> None:
    result = run_one(planned(DAY), [checkin(16, 51, 0)])
    assert (result.outcome, result.minutes_late) == (Outcome.LATE, 11)


def test_kitchen_uses_its_own_entry_time() -> None:
    cook = employee(area=Area.KITCHEN)
    assert run_one(planned(DAY), [checkin(16, 40, 59)], cook).outcome == Outcome.OK
    late = run_one(planned(DAY), [checkin(16, 41, 0)], cook)
    assert (late.outcome, late.minutes_late) == (Outcome.LATE, 11)


def test_first_checkin_of_the_day_counts() -> None:
    result = run_one(planned(DAY), [checkin(16, 55), checkin(16, 35)])
    assert (result.outcome, result.checkin) == (Outcome.OK, at(16, 35))


def test_checkin_on_another_day_does_not_count() -> None:
    result = run_one(planned(DAY), [checkin(16, 35, day=date(2026, 9, 24))])
    assert result.outcome == Outcome.ABSENT


def test_employee_without_lateness_is_never_late() -> None:
    result = run_one(planned(DAY), [checkin(18, 0)], employee(applies_lateness=False))
    assert result.outcome == Outcome.OK


def test_missing_checkin_is_absent() -> None:
    assert run_one(planned(DAY), []).outcome == Outcome.ABSENT


def test_present_without_checkin_is_ok() -> None:
    assert run_one(planned(DAY, present_no_checkin=True), []).outcome == Outcome.OK


def test_today_before_limit_is_pending() -> None:
    result = run_one(planned(DAY), [], today=DAY, now=at(16, 50, 30))
    assert result.outcome == Outcome.PENDING


def test_today_after_limit_without_checkin_is_absent() -> None:
    result = run_one(planned(DAY), [], today=DAY, now=at(16, 51))
    assert result.outcome == Outcome.ABSENT


def test_today_with_checkin_is_evaluated() -> None:
    result = run_one(planned(DAY), [checkin(16, 45)], today=DAY, now=at(16, 46))
    assert result.outcome == Outcome.OK


def test_future_days() -> None:
    result = run_one(planned(DAY), [], today=date(2026, 9, 22))
    assert result.outcome == Outcome.FUTURE


def test_rest_day_with_checkin_is_unregistered_change() -> None:
    result = run_one(planned(DAY, Planned.REST), [checkin(16, 45)])
    assert (result.outcome, result.checkin) == (Outcome.UNREGISTERED_CHANGE, at(16, 45))


def test_rest_day_without_checkin_is_rest() -> None:
    assert run_one(planned(DAY, Planned.REST), []).outcome == Outcome.REST


def test_closed_day_ignores_checkin() -> None:
    assert run_one(planned(DAY, Planned.CLOSED), [checkin(18, 0)]).outcome == Outcome.CLOSED


def test_planned_absence_is_justified_with_rh_type() -> None:
    result = run_one(planned(DAY, Planned.ABSENCE, rh_type=RhType.INCAPACIDAD), [])
    assert (result.outcome, result.rh_type) == (Outcome.JUSTIFIED, RhType.INCAPACIDAD)


def test_manual_absence_is_absent_even_with_checkin() -> None:
    result = run_one(planned(DAY, manual_absence=True), [checkin(16, 30)])
    assert result.outcome == Outcome.ABSENT


def test_untracked_employee_counts_as_present() -> None:
    manager = replace(employee(tracks_attendance=False, applies_lateness=False), sr_id=None)
    assert run_one(planned(DAY), [], manager).outcome == Outcome.OK


def test_unmapped_checkins_are_reported() -> None:
    _, warnings = compare(
        [planned(DAY)],
        [employee()],
        [checkin(16, 40, sr_id=999)],
        DEFAULT_SETTINGS,
        date(2026, 9, 27),
        EVENING,
    )
    assert [(w.code, w.day) for w in warnings] == [(WarningCode.UNMAPPED_CHECKIN, DAY)]
    assert "999" in warnings[0].detail


def test_checkins_of_deactivated_employee_are_reported_not_lost() -> None:
    # Review Focus #2: employee 2 is inactive, so it has no planned days.
    inactive = employee(2, active=False)
    _, warnings = compare(
        [planned(DAY)],
        [employee(1), inactive],
        [checkin(16, 40, sr_id=102)],
        DEFAULT_SETTINGS,
        date(2026, 9, 27),
        EVENING,
    )
    assert [w.code for w in warnings] == [WarningCode.UNMAPPED_CHECKIN]


def test_employee_without_sr_id_that_tracks_attendance_is_warned_once() -> None:
    no_sr_id = replace(employee(1, tracks_attendance=True), sr_id=None)
    day_two = date(2026, 9, 24)
    _, warnings = compare(
        [planned(DAY, employee_id=1), planned(day_two, employee_id=1)],
        [no_sr_id],
        [],
        DEFAULT_SETTINGS,
        date(2026, 9, 27),
        EVENING,
    )
    assert [(w.code, w.employee_id, w.day) for w in warnings] == [(WarningCode.NO_SR_ID, 1, DAY)]
    assert "E1" in warnings[0].detail


def test_employee_without_sr_id_that_does_not_track_attendance_is_not_warned() -> None:
    manager = replace(employee(1, tracks_attendance=False), sr_id=None)
    _, warnings = compare(
        [planned(DAY, employee_id=1)],
        [manager],
        [],
        DEFAULT_SETTINGS,
        date(2026, 9, 27),
        EVENING,
    )
    assert warnings == []


def test_result_keeps_the_planned_exception() -> None:
    absence = exception(ExceptionKind.WORK_TO_ABSENCE, DAY, rh_type=RhType.VACACIONES)
    day_plan = replace(planned(DAY, Planned.ABSENCE, rh_type=RhType.VACACIONES), exception=absence)
    result = run_one(day_plan, [])
    assert (result.outcome, result.exception) == (Outcome.JUSTIFIED, absence)


def test_late_result_keeps_a_present_no_checkin_exception() -> None:
    present = exception(ExceptionKind.PRESENT_NO_CHECKIN, DAY)
    day_plan = replace(planned(DAY, present_no_checkin=True), exception=present)
    result = run_one(day_plan, [checkin(17, 5)])
    assert (result.outcome, result.exception) == (Outcome.LATE, present)
