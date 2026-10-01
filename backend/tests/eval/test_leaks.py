from dataclasses import replace

from tabernas.domain.types import Area, Employee
from tests.eval.leaks import leaked_names

ANA = Employee(1, 10, "ANA PRUEBA", "María Ángeles Prueba Díaz", Area.OTHER, True, True, True)


def test_clean_payload_with_aliases_passes() -> None:
    assert leaked_names('{"text": "{E1} llegó tarde; de la sala"}', [ANA]) == []


def test_part_of_a_name_is_a_leak_even_accent_and_case_folded() -> None:
    assert leaked_names("avisó maria por teléfono", [ANA]) == ["maria"]
    assert "angeles" in leaked_names("ÁNGELES", [ANA])


def test_full_name_is_a_leak() -> None:
    assert "<nombre completo>" in leaked_names("Habló con Ana Prueba", [ANA])


def test_connectors_short_parts_and_substrings_are_ignored() -> None:
    other = replace(ANA, short_name="LUIS DE LA PAZ", rh_name=None)
    assert leaked_names("de la; pazos; el", [other]) == []
    assert leaked_names("de la paz", [other]) == ["paz"]


def test_parts_containing_d_are_detected() -> None:
    assert "diaz" in leaked_names("habló con DÍAZ", [ANA])
