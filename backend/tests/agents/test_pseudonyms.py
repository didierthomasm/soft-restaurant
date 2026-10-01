from tabernas.agents.pseudonyms import (
    alias,
    aliases_in,
    contains_known_name,
    parse_alias,
    render,
    scrub,
)
from tests.agents.helpers import STAFF, person


def test_alias_round_trip() -> None:
    assert alias(12) == "E12"
    assert parse_alias("E12") == 12
    assert parse_alias(" E7 ") == 7
    for bad in ("E", "12", "{E12}", "e12x", "Ana"):
        assert parse_alias(bad) is None


def test_aliases_in_only_reads_braced_tokens() -> None:
    assert aliases_in("Hablar con {E1} y {E22}; E3 sin llaves no cuenta") == {"E1", "E22"}


def test_render_uses_short_names_and_keeps_unknown_aliases() -> None:
    text = "{E1} cubrió a {E2}; {E9} ya no existe"
    assert render(text, STAFF) == "ANA PRUEBA cubrió a BETO PRUEBA; {E9} ya no existe"


def test_scrub_replaces_short_and_rh_names_ignoring_case() -> None:
    text = "Avisó ana prueba lopez que cubría a Beto Prueba y a ALBERTO PRUEBA RUIZ"
    assert scrub(text, STAFF) == "Avisó E1 que cubría a E2 y a E2"


def test_scrub_prefers_the_longest_name_and_whole_words() -> None:
    employees = [person(1, "ANA"), person(2, "ANA MARIA")]
    assert scrub("ANA MARIA y ANA comieron BANANA", employees) == "E2 y E1 comieron BANANA"


def test_scrub_without_employees_changes_nothing() -> None:
    assert scrub("hola", []) == "hola"


def test_contains_known_name_ignores_alias_tokens() -> None:
    assert not contains_known_name("Revisar con {E1}.", STAFF)
    assert contains_known_name("Revisar con Ana Prueba.", STAFF)
    assert not contains_known_name("Revisar con alguien.", [])
