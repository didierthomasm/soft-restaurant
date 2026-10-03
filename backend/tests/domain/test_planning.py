from datetime import date

from tabernas.domain.planning import planned_calendar
from tabernas.domain.types import (
    AttendanceWarning,
    ExceptionKind,
    Planned,
    PlannedDay,
    RhType,
    WarningCode,
)
from tests.domain.factories import WEEK_39, employee, exception, rule


def by_day(planned: list[PlannedDay], employee_id: int = 1) -> dict[date, PlannedDay]:
    return {p.day: p for p in planned if p.employee_id == employee_id}


def test_fixed_weekday_is_rest_every_week() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 21), date(2026, 10, 4))
    days = by_day(planned)
    assert days[date(2026, 9, 22)].planned == Planned.REST
    assert days[date(2026, 9, 29)].planned == Planned.REST


def test_extra_weekday_is_rest_only_on_double_weeks() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 21), date(2026, 10, 12))
    days = by_day(planned)
    assert days[date(2026, 9, 21)].planned == Planned.WORK
    assert days[date(2026, 9, 28)].planned == Planned.REST
    assert days[date(2026, 10, 5)].planned == Planned.WORK
    assert days[date(2026, 10, 12)].planned == Planned.REST


def test_two_weeks_have_eleven_working_days() -> None:
    planned, _ = planned_calendar([employee()], [rule()], [], date(2026, 9, 28), date(2026, 10, 11))
    assert sum(p.planned == Planned.WORK for p in planned) == 11


def test_rule_validity_switches_rules() -> None:
    rules = [
        rule(fixed=1, valid_to=date(2026, 9, 27), id=1),
        rule(fixed=3, valid_from=date(2026, 9, 28), id=2),
    ]
    planned, warnings = planned_calendar(
        [employee()], rules, [], date(2026, 9, 21), date(2026, 10, 4)
    )
    days = by_day(planned)
    assert days[date(2026, 9, 22)].planned == Planned.REST  # Tue under rule 1
    assert days[date(2026, 9, 29)].planned == Planned.WORK  # Tue under rule 2
    assert days[date(2026, 10, 1)].planned == Planned.REST  # Thu under rule 2
    assert warnings == []


def test_missing_rule_plans_work_and_warns_once() -> None:
    planned, warnings = planned_calendar([employee()], [], [], *WEEK_39)
    assert {p.planned for p in planned} == {Planned.WORK}
    assert warnings == [
        AttendanceWarning(
            WarningCode.NO_REST_RULE, 1, date(2026, 9, 21), "Sin regla de descanso vigente"
        )
    ]


def test_store_closed_applies_to_everyone_and_wins() -> None:
    closed_day = date(2026, 9, 24)
    exceptions = [
        exception(ExceptionKind.STORE_CLOSED, closed_day, comment="Ley Seca", id=1),
        exception(ExceptionKind.REST_TO_WORK, closed_day, employee_id=1, id=2),
    ]
    planned, _ = planned_calendar(
        [employee(1), employee(2)], [rule(1), rule(2, id=2)], exceptions, *WEEK_39
    )
    closed = [p for p in planned if p.day == closed_day]
    assert [(p.employee_id, p.planned, p.comment) for p in closed] == [
        (1, Planned.CLOSED, "Ley Seca"),
        (2, Planned.CLOSED, "Ley Seca"),
    ]


def test_closure_range_covers_every_day() -> None:
    closure = exception(ExceptionKind.STORE_CLOSED, date(2026, 12, 24), until=date(2026, 12, 25))
    planned, _ = planned_calendar(
        [employee()], [rule()], [closure], date(2026, 12, 21), date(2026, 12, 27)
    )
    days = by_day(planned)
    assert days[date(2026, 12, 24)].planned == Planned.CLOSED
    assert days[date(2026, 12, 25)].planned == Planned.CLOSED
    assert days[date(2026, 12, 26)].planned == Planned.WORK


def test_work_to_absence_is_planned_absence_with_rh_type() -> None:
    vacation = exception(
        ExceptionKind.WORK_TO_ABSENCE,
        date(2026, 9, 23),
        until=date(2026, 9, 25),
        rh_type=RhType.VACACIONES,
        comment="Vacaciones",
    )
    planned, _ = planned_calendar([employee()], [rule()], [vacation], *WEEK_39)
    absent = [p for p in planned if p.planned == Planned.ABSENCE]
    assert [p.day.day for p in absent] == [23, 24, 25]
    assert {(p.rh_type, p.comment) for p in absent} == {(RhType.VACACIONES, "Vacaciones")}


def test_manual_absence_plans_work_flagged() -> None:
    manual = exception(ExceptionKind.MANUAL_ABSENCE, date(2026, 9, 23))
    planned, _ = planned_calendar([employee()], [rule()], [manual], *WEEK_39)
    day = by_day(planned)[date(2026, 9, 23)]
    assert (day.planned, day.manual_absence) == (Planned.WORK, True)


def test_rest_to_work_turns_rest_day_into_work() -> None:
    swap = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22))
    planned, _ = planned_calendar([employee()], [rule()], [swap], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 22)].planned == Planned.WORK


def test_present_no_checkin_only_flags_the_day() -> None:
    flag = exception(ExceptionKind.PRESENT_NO_CHECKIN, date(2026, 9, 23))
    planned, _ = planned_calendar([employee()], [rule()], [flag], *WEEK_39)
    day = by_day(planned)[date(2026, 9, 23)]
    assert (day.planned, day.present_no_checkin) == (Planned.WORK, True)


def test_other_employees_exceptions_do_not_apply() -> None:
    swap = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22), employee_id=2)
    planned, _ = planned_calendar([employee(1)], [rule(1)], [swap], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 22)].planned == Planned.REST


def test_inactive_employees_are_not_planned() -> None:
    planned, _ = planned_calendar([employee(active=False)], [rule()], [], *WEEK_39)
    assert planned == []


def test_output_is_sorted_by_employee_then_day() -> None:
    planned, _ = planned_calendar(
        [employee(2), employee(1)], [rule(1), rule(2, id=2)], [], *WEEK_39
    )
    assert [(p.employee_id, p.day.day) for p in planned][:2] == [(1, 21), (1, 22)]
    assert planned[7].employee_id == 2


def test_each_employee_exception_travels_with_its_day() -> None:
    absence = exception(
        ExceptionKind.WORK_TO_ABSENCE,
        date(2026, 9, 23),
        until=date(2026, 9, 24),
        rh_type=RhType.VACACIONES,
        id=5,
    )
    manual = exception(ExceptionKind.MANUAL_ABSENCE, date(2026, 9, 25), id=6)
    extra = exception(ExceptionKind.REST_TO_WORK, date(2026, 9, 22), id=7)  # Tue = rest
    present = exception(ExceptionKind.PRESENT_NO_CHECKIN, date(2026, 9, 26), id=8)
    planned, _ = planned_calendar(
        [employee()], [rule()], [absence, manual, extra, present], *WEEK_39
    )
    days = by_day(planned)
    assert days[date(2026, 9, 23)].exception == absence
    assert days[date(2026, 9, 24)].exception == absence  # same object for the whole range
    assert days[date(2026, 9, 25)].exception == manual
    assert days[date(2026, 9, 22)].exception == extra
    assert days[date(2026, 9, 26)].exception == present
    assert days[date(2026, 9, 21)].exception is None


def test_store_closure_is_not_the_employee_exception() -> None:
    closure = exception(ExceptionKind.STORE_CLOSED, date(2026, 9, 24), id=1)
    planned, _ = planned_calendar([employee()], [rule()], [closure], *WEEK_39)
    assert by_day(planned)[date(2026, 9, 24)].exception is None
