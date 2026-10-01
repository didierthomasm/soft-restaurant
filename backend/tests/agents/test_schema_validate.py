import json
from datetime import date

import pytest

from tabernas.agents.weekly_review.schema import (
    NARRATIVE_SCHEMA,
    NarrativeFormatError,
    parse_narrative,
)
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    SuggestedAction,
)
from tests.agents.helpers import STAFF

F1 = Finding(
    "ABSENT_NO_EXCEPTION:1:2026-09-23", FindingKind.ABSENT_NO_EXCEPTION, 1, (date(2026, 9, 23),)
)
F2 = Finding("REST_DAY_CHECKIN:2:2026-09-22", FindingKind.REST_DAY_CHECKIN, 2, (date(2026, 9, 22),))


def item(finding_id: str, explanation: str = "Revisar a {E1}.") -> NarrativeItem:
    return NarrativeItem(finding_id, Priority.HIGH, explanation, SuggestedAction.JUSTIFY)


def narrative(*items: NarrativeItem, summary: str = "Pendientes de {E1} y {E2}.") -> Narrative:
    return Narrative(summary, items)


def test_schema_is_closed_and_matches_the_domain_enums() -> None:
    item_schema = NARRATIVE_SCHEMA["properties"]["items"]["items"]
    assert NARRATIVE_SCHEMA["additionalProperties"] is False
    assert item_schema["additionalProperties"] is False
    assert item_schema["properties"]["priority"]["enum"] == [p.value for p in Priority]
    assert item_schema["properties"]["suggested_action"]["enum"] == [
        a.value for a in SuggestedAction
    ]
    assert "$ref" not in json.dumps(NARRATIVE_SCHEMA)


def test_parse_valid_narrative() -> None:
    text = json.dumps(
        {
            "summary": "  Una falta.  ",
            "items": [
                {
                    "finding_id": F1.id,
                    "priority": "HIGH",
                    "explanation": " Falta de {E1}. ",
                    "suggested_action": "JUSTIFY",
                }
            ],
        }
    )
    assert parse_narrative(text) == Narrative(
        "Una falta.",
        (NarrativeItem(F1.id, Priority.HIGH, "Falta de {E1}.", SuggestedAction.JUSTIFY),),
    )


@pytest.mark.parametrize(
    "text",
    [
        "no es json",
        '{"summary": "x"}',
        '{"summary": "x", "items": [], "extra": 1}',
        '{"summary": "x", "items": [{"finding_id": "a", "priority": "URGENT", '
        '"explanation": "", "suggested_action": "NONE"}]}',
    ],
)
def test_parse_rejects_bad_payloads(text: str) -> None:
    with pytest.raises(NarrativeFormatError, match="no cumple el esquema"):
        parse_narrative(text)


def test_complete_narrative_is_valid() -> None:
    answer = narrative(item(F1.id), item(F2.id, "Cambio de descanso de {E2}."))
    assert validate_narrative(answer, [F1, F2], STAFF) == []


def test_week_without_findings_accepts_empty_items() -> None:
    assert validate_narrative(narrative(summary="Semana sin pendientes."), [], STAFF) == []


def test_missing_repeated_and_unknown_findings_are_reported() -> None:
    answer = narrative(item(F1.id), item(F1.id), item("INVENTADO:1:-"))
    errors = validate_narrative(answer, [F1, F2], STAFF)
    assert f"Faltan hallazgos: {F2.id}" in errors
    assert f"Hallazgos repetidos: {F1.id}" in errors
    assert "Hallazgos que no existen: INVENTADO:1:-" in errors


def test_unknown_alias_is_reported() -> None:
    errors = validate_narrative(narrative(item(F1.id, "Habló con {E99}.")), [F1], STAFF)
    assert errors == ["Seudónimos desconocidos: {E99}"]


def test_real_names_are_reported() -> None:
    errors = validate_narrative(narrative(item(F1.id), summary="Ana Prueba faltó."), [F1], STAFF)
    assert len(errors) == 1 and "nombres reales" in errors[0]


def test_blank_summary_is_reported() -> None:
    assert validate_narrative(narrative(item(F1.id), summary="  "), [F1], STAFF) == [
        "El resumen está vacío."
    ]
