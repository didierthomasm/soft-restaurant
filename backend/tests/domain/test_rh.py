from datetime import date

import pytest

from tabernas.domain.rh import rh_type_for, to_rh_rows
from tabernas.domain.types import DayResult, Outcome, RhType, WarningCode
from tests.domain.factories import employee, result


@pytest.mark.parametrize(
    ("day_result", "expected"),
    [
        (result(Outcome.LATE), RhType.RETARDO),
        (result(Outcome.LATE, justification_id=7, rh_type=RhType.NO_CAPTURAR), RhType.NO_CAPTURAR),
        (result(Outcome.ABSENT), RhType.FALTA_INJUSTIFICADA),
        (result(Outcome.ABSENT, justification_id=7, rh_type=RhType.VACACIONES), RhType.VACACIONES),
        (result(Outcome.JUSTIFIED, rh_type=RhType.DESCANSO), RhType.DESCANSO),
        (result(Outcome.OK), None),
        (result(Outcome.REST), None),
        (result(Outcome.CLOSED), None),
        (result(Outcome.UNREGISTERED_CHANGE), None),
        (result(Outcome.PENDING), None),
        (result(Outcome.FUTURE), None),
    ],
)
def test_rh_type_for(day_result: DayResult, expected: RhType | None) -> None:
    assert rh_type_for(day_result) == expected


def test_rows_skip_no_capturar_and_sort_by_name_then_day() -> None:
    employees = [employee(1, rh_name="ZAPATA"), employee(2, rh_name="ALVAREZ")]
    results = [
        result(Outcome.LATE, employee_id=1, day=date(2026, 9, 24)),
        result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 23)),
        result(Outcome.LATE, employee_id=2, justification_id=7, rh_type=RhType.NO_CAPTURAR),
        result(Outcome.ABSENT, employee_id=2, day=date(2026, 9, 25), comment="Sin aviso"),
        result(Outcome.OK, employee_id=2),
    ]
    rows, warnings = to_rh_rows(results, employees)
    assert [(r.name, r.day.day, r.rh_type, r.comment) for r in rows] == [
        ("ALVAREZ", 25, RhType.FALTA_INJUSTIFICADA, "Sin aviso"),
        ("ZAPATA", 23, RhType.FALTA_INJUSTIFICADA, ""),
        ("ZAPATA", 24, RhType.RETARDO, ""),
    ]
    assert warnings == []


def test_missing_rh_name_falls_back_to_short_name_and_warns_once() -> None:
    results = [
        result(Outcome.ABSENT, day=date(2026, 9, 23)),
        result(Outcome.ABSENT, day=date(2026, 9, 24)),
    ]
    rows, warnings = to_rh_rows(results, [employee(1, rh_name=None)])
    assert {r.name for r in rows} == {"E1"}
    assert [(w.code, w.employee_id) for w in warnings] == [(WarningCode.MISSING_RH_NAME, 1)]
