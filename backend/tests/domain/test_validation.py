from datetime import date, time

import pytest

from tabernas.domain.types import ExceptionKind, Incident, RhType
from tabernas.domain.validation import (
    DomainValidationError,
    format_hhmm,
    parse_hhmm,
    validate_exception,
    validate_justification,
    validate_rest_rule,
    validate_tolerance,
)

MONDAY = date(2026, 9, 28)


def _rule(**overrides: object) -> None:
    fields: dict[str, object] = {
        "fixed_weekday": 1,
        "extra_weekday": 0,
        "double_rest_anchor": MONDAY,
        "valid_from": date(2026, 1, 1),
        "valid_to": None,
    }
    validate_rest_rule(**{**fields, **overrides})  # type: ignore[arg-type]


def test_valid_rest_rule_passes() -> None:
    _rule()


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"fixed_weekday": 7}, "entre 0"),
        ({"extra_weekday": -1}, "entre 0"),
        ({"extra_weekday": 1}, "distintos"),
        ({"double_rest_anchor": date(2026, 9, 29)}, "lunes"),
        ({"valid_to": date(2025, 12, 31)}, "vigencia"),
    ],
)
def test_invalid_rest_rules(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        _rule(**overrides)


def _exception(**overrides: object) -> None:
    fields: dict[str, object] = {
        "kind": ExceptionKind.WORK_TO_ABSENCE,
        "employee_id": 1,
        "rh_type": RhType.VACACIONES,
        "date_from": MONDAY,
        "date_to": MONDAY,
    }
    validate_exception(**{**fields, **overrides})  # type: ignore[arg-type]


def test_valid_exceptions_pass() -> None:
    _exception()
    _exception(kind=ExceptionKind.STORE_CLOSED, employee_id=None, rh_type=None)
    _exception(kind=ExceptionKind.REST_TO_WORK, rh_type=None)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"date_to": date(2026, 9, 27)}, "anterior"),
        ({"kind": ExceptionKind.STORE_CLOSED, "rh_type": None}, "aplica a todos"),
        ({"employee_id": None}, "aplica a todos"),
        ({"rh_type": None}, "tipo de ausencia"),
        ({"rh_type": RhType.RETARDO}, "tipo de ausencia"),
        ({"kind": ExceptionKind.REST_TO_WORK}, "Solo las ausencias"),
    ],
)
def test_invalid_exceptions(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        _exception(**overrides)


def test_justification_rh_types_depend_on_incident() -> None:
    validate_justification(incident=Incident.LATE, rh_type=RhType.NO_CAPTURAR)
    validate_justification(incident=Incident.ABSENT, rh_type=RhType.INCAPACIDAD)
    with pytest.raises(DomainValidationError):
        validate_justification(incident=Incident.LATE, rh_type=RhType.VACACIONES)
    with pytest.raises(DomainValidationError):
        validate_justification(incident=Incident.ABSENT, rh_type=RhType.RETARDO)


def test_hhmm_round_trip_and_errors() -> None:
    assert parse_hhmm("16:40") == time(16, 40)
    assert format_hhmm(time(9, 5)) == "09:05"
    for bad in ("25:00", "16:60", "1640", "4:40", "aa:bb"):
        with pytest.raises(DomainValidationError, match="HH:MM"):
            parse_hhmm(bad)


def test_tolerance_bounds() -> None:
    validate_tolerance(0)
    validate_tolerance(60)
    with pytest.raises(DomainValidationError):
        validate_tolerance(61)
    with pytest.raises(DomainValidationError):
        validate_tolerance(-1)
