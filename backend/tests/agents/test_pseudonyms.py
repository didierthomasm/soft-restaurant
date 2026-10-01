import unicodedata

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


# Accent and spacing tolerance tests
def test_scrub_accepts_unaccented_variants() -> None:
    employees = [person(1, "JOSÉ PÉREZ")]
    # Unaccented variant should be scrubbed
    assert scrub("Avisó JOSE PEREZ", employees) == "Avisó E1"
    # Mixed accents should be scrubbed
    assert scrub("Jose Pérez", employees) == "E1"
    # Original accented should be scrubbed
    assert scrub("JOSÉ PÉREZ", employees) == "E1"


def test_scrub_accepts_nfd_composed_variants() -> None:
    employees = [person(1, "JOSÉ")]
    # NFD-composed: é is decomposed to e + combining acute
    nfd_text = unicodedata.normalize("NFD", "JOSÉ")
    assert scrub(nfd_text, employees) == "E1"
    # NFC-composed: é as single character
    nfc_text = unicodedata.normalize("NFC", "JOSÉ")
    assert scrub(nfc_text, employees) == "E1"


def test_scrub_accepts_whitespace_variants() -> None:
    employees = [person(1, "ANA PRUEBA")]
    # Double space
    assert scrub("Avisó ANA  PRUEBA que", employees) == "Avisó E1 que"
    # Newline between words
    assert scrub("Avisó ANA\nPRUEBA que", employees) == "Avisó E1 que"
    # Tab between words
    assert scrub("Avisó ANA\tPRUEBA que", employees) == "Avisó E1 que"


def test_scrub_accepts_hyphen_variants() -> None:
    employees = [person(1, "ANA-PRUEBA")]
    assert scrub("Avisó ANA-PRUEBA que", employees) == "Avisó E1 que"
    assert scrub("Avisó ANA PRUEBA que", employees) == "Avisó E1 que"


def test_scrub_replaces_first_names_alone() -> None:
    employees = [
        person(1, "ANA PRUEBA", "ANA PRUEBA LOPEZ"),
        person(2, "BETO PRUEBA", "ALBERTO PRUEBA RUIZ"),
    ]
    # First name "Ana" should be replaced with E1 (only ANA in the list has "ANA")
    assert scrub("Avisó Ana que cubría", employees) == "Avisó E1 que cubría"
    # "Beto" should be replaced with E2
    assert scrub("Con Beto y Ana", employees) == "Con E2 y E1"


def test_scrub_replaces_shared_surname_as_placeholder() -> None:
    employees = [
        person(1, "ANA PRUEBA"),
        person(2, "BETO PRUEBA"),
    ]
    # "PRUEBA" is shared by both → replace with [empleado]
    assert scrub("Hablamos con los PRUEBA", employees) == "Hablamos con los [empleado]"


def test_scrub_leaves_connector_words_untouched() -> None:
    employees = [person(1, "MARIA DE LOS ANGELES")]
    # "de" and "los" are connectors (skipped in token extraction)
    # So "de los" alone should not be scrubbed
    assert scrub("la de los", employees) == "la de los"
    # But full name with connectors should be scrubbed
    assert scrub("Avisó MARIA DE LOS ANGELES", employees) == "Avisó E1"


def test_scrub_connector_words_not_scrubbed_from_rh_name() -> None:
    employees = [person(1, "ANA", "MARIA DE LOURDES")]
    # Single "Maria" from RH name should be scrubbed
    assert scrub("Maria vino", employees) == "E1 vino"
    # "LOURDES" is a token from "MARIA DE LOURDES", so it gets scrubbed
    # But "de" is a connector, so it stays
    assert scrub("la de lourdes", employees) == "la de E1"


def test_contains_known_name_with_accents() -> None:
    employees = [person(1, "JOSÉ PÉREZ")]
    # Should detect unaccented variant
    assert contains_known_name("Revisar con JOSE PEREZ", employees)
    # Should detect accented variant
    assert contains_known_name("Revisar con JOSÉ PÉREZ", employees)
    # Should detect mixed
    assert contains_known_name("Revisar con Jose Pérez", employees)


def test_contains_known_name_with_spacing() -> None:
    employees = [person(1, "ANA PRUEBA")]
    # Should detect double space
    assert contains_known_name("Revisar con ANA  PRUEBA", employees)
    # Should detect newline
    assert contains_known_name("Revisar con ANA\nPRUEBA", employees)


def test_contains_known_name_not_flagging_first_name_alone() -> None:
    employees = [
        person(1, "ANA PRUEBA"),
        person(2, "BETO FRANCO"),
    ]
    # "Ana" alone should not be flagged (only full names are checked)
    assert not contains_known_name("Revisar con Ana", employees)
    # But full name should be flagged
    assert contains_known_name("Revisar con Ana Prueba", employees)


def test_scrub_surnames_after_connectors() -> None:
    employees = [person(1, "JUAN DE LA CRUZ")]
    # CRUZ is a surname after connector, should be scrubbed as a token
    assert scrub("vio a CRUZ y a Juan", employees) == "vio a E1 y a E1"
    # Full name should also be scrubbed
    assert scrub("Avisó JUAN DE LA CRUZ", employees) == "Avisó E1"


def test_scrub_with_special_letter_n_tilde() -> None:
    employees = [person(1, "MUÑOZ NUÑEZ")]
    # Full name "Muñoz Nuñez" should be scrubbed as a whole
    assert scrub("avisó Muñoz Nuñez", employees) == "avisó E1"
    # Plain N variant should also match the full name
    assert scrub("avisó MUNOZ NUNEZ", employees) == "avisó E1"
    # NFD-decomposed text: the name part is scrubbed, but other combining marks stay
    nfd_text = unicodedata.normalize("NFD", "avisó Muñoz Nuñez")
    nfd_result = scrub(nfd_text, employees)
    # Result should have "E1" in place of the name, with "aviso" + combining accent
    assert "E1" in nfd_result and "Muñoz" not in nfd_result and "Nuñez" not in nfd_result
    # Individual tokens should be scrubbed
    assert scrub("vio a Nuñez y a Muñoz", employees) == "vio a E1 y a E1"


def test_contains_known_name_with_n_tilde() -> None:
    employees = [person(1, "MUÑOZ NUÑEZ")]
    # Should detect Ñ in employee name
    assert contains_known_name("Revisar con Muñoz Nuñez", employees)
    # Should detect plain N variant
    assert contains_known_name("Revisar con Munoz Nunez", employees)
    # Should detect mixed accents
    assert contains_known_name("Revisar con MUÑOZ nunez", employees)
