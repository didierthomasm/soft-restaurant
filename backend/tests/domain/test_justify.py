from datetime import date

from tabernas.domain.justify import apply_justifications, default_rh_type
from tabernas.domain.types import Incident, Outcome, RhType, WarningCode
from tests.domain.factories import DAY, justification, result


def test_default_rh_types() -> None:
    assert default_rh_type(Incident.LATE) == RhType.NO_CAPTURAR
    assert default_rh_type(Incident.ABSENT) == RhType.FALTA_JUSTIFICADA


def test_justification_marks_matching_incident() -> None:
    results, warnings = apply_justifications(
        [result(Outcome.ABSENT)], [justification(Incident.ABSENT, RhType.INCAPACIDAD)]
    )
    assert (results[0].justification_id, results[0].rh_type, results[0].comment) == (
        7,
        RhType.INCAPACIDAD,
        "Cita médica",
    )
    assert results[0].outcome == Outcome.ABSENT
    assert warnings == []


def test_justification_needs_same_incident_type() -> None:
    original = result(Outcome.ABSENT)
    results, warnings = apply_justifications(
        [original], [justification(Incident.LATE, RhType.NO_CAPTURAR)]
    )
    assert results == [original]
    assert [(w.code, w.employee_id, w.day) for w in warnings] == [
        (WarningCode.ORPHAN_JUSTIFICATION, 1, DAY)
    ]


def test_justification_for_other_employee_or_day_does_not_apply() -> None:
    original = result(Outcome.LATE)
    others = [
        justification(Incident.LATE, RhType.NO_CAPTURAR, employee_id=2, id=1),
        justification(Incident.LATE, RhType.NO_CAPTURAR, day=date(2026, 9, 24), id=2),
    ]
    results, warnings = apply_justifications([original], others)
    assert results == [original]
    assert len(warnings) == 2
