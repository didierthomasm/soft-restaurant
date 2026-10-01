"""Pseudonyms (spec E4): Claude only ever sees E{id}, never an employee's name."""

import re
import unicodedata
from collections.abc import Sequence

from tabernas.domain.types import Employee

_ALIAS = re.compile(r"E(\d+)")
_ALIAS_TOKEN = re.compile(r"\{(E\d+)\}")

# Connector words to exclude from individual token scrubbing
_CONNECTORS = {"de", "del", "la", "las", "los", "san", "y"}


def alias(employee_id: int) -> str:
    return f"E{employee_id}"


def parse_alias(value: str) -> int | None:
    match = _ALIAS.fullmatch(value.strip())
    return int(match.group(1)) if match else None


def aliases_in(text: str) -> set[str]:
    return set(_ALIAS_TOKEN.findall(text))


def render(text: str, employees: Sequence[Employee]) -> str:
    names = {alias(e.id): e.short_name for e in employees}
    return _ALIAS_TOKEN.sub(lambda m: names.get(m.group(1), m.group(0)), text)


def scrub(text: str, employees: Sequence[Employee]) -> str:
    """Replace employee names with pseudonyms (E{id}) or [empleado] for shared tokens.

    Tolerant to accents, spacing, and hyphens. Replaces full names first (longest),
    then individual name tokens (≥3 chars, excluding connectors).
    """
    if not employees:
        return text

    result = text

    # Step 1: Replace full names (longest first)
    full_names = []
    for employee in employees:
        for name in (employee.short_name, employee.rh_name):
            if name and name.strip():
                full_names.append((name.strip(), employee.id))

    # Sort by length (longest first) to prefer "ANA MARIA" over "ANA"
    full_names.sort(key=lambda x: len(x[0]), reverse=True)

    for name, emp_id in full_names:
        pattern = _accent_tolerant_pattern(name)
        result = pattern.sub(alias(emp_id), result)

    # Step 2: Extract and map individual tokens
    token_map: dict[str, int | str] = {}  # token → employee_id or "[empleado]"

    for employee in employees:
        for name in (employee.short_name, employee.rh_name):
            if name and name.strip():
                tokens = _extract_tokens(name)
                for token in tokens:
                    if token not in token_map:
                        token_map[token] = employee.id
                    elif token_map[token] != employee.id:
                        # Shared token → mark as [empleado]
                        token_map[token] = "[empleado]"

    # Step 3: Replace individual tokens
    for token, replacement in sorted(token_map.items(), key=lambda x: len(x[0]), reverse=True):
        repl_str = alias(replacement) if isinstance(replacement, int) else replacement
        pattern = _accent_tolerant_pattern(token)
        result = pattern.sub(repl_str, result)

    return result


def contains_known_name(text: str, employees: Sequence[Employee]) -> bool:
    """Check if text contains any employee's full short or RH name.

    Ignores {E12} alias tokens. Tolerant to accents, spacing, and hyphens.
    Only checks full names, not individual tokens.
    """
    # Remove alias tokens first
    text_without_aliases = _ALIAS_TOKEN.sub(" ", text)

    for employee in employees:
        for name in (employee.short_name, employee.rh_name):
            if name and name.strip():
                pattern = _accent_tolerant_pattern(name.strip())
                if pattern.search(text_without_aliases):
                    return True

    return False


def _strip_accents(text: str) -> str:
    """Remove accents using NFKD normalization and combining character removal."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _accent_tolerant_pattern(name: str) -> re.Pattern[str]:
    """Build regex pattern tolerant to accents, spacing, and hyphens.

    Matches:
    - Case-insensitive variants
    - Accented variants (JOSÉ, Jose, jose, JOSE, etc.)
    - Whitespace/hyphen variants
    - NFD-decomposed forms (letter + optional combining marks)
    """
    stripped = _strip_accents(name.strip())

    # Map each character to its accent-tolerant class with optional combining marks
    pattern_parts = []
    i = 0
    while i < len(stripped):
        char = stripped[i]
        char_upper = char.upper()

        if char_upper in "AEIOUÑC":
            # Vowels and special characters with accented variants
            # Allow optional combining marks after the character
            accent_class = _get_accent_class(char_upper)
            # Remove outer brackets and add combining mark pattern, then re-bracket
            inner = accent_class[1:-1]  # Remove [ and ]
            pattern_parts.append(f"[{inner}][̀-ͯ]*")
        elif char.isspace() or char == "-":
            # Space or hyphen → match any whitespace/hyphen sequence
            pattern_parts.append(r"[\s\-]+")
        else:
            # Regular character with optional combining marks
            escaped = re.escape(char)
            pattern_parts.append(f"{escaped}[̀-ͯ]*")

        i += 1

    pattern_str = "".join(pattern_parts)
    # Word boundaries: before must not be word char, after must not be word char
    return re.compile(rf"(?<!\w)({pattern_str})(?!\w)", re.IGNORECASE)


def _get_accent_class(char: str) -> str:
    """Return regex character class for accented variants of a letter."""
    classes = {
        "A": "[aáàäâãAÁÀÄÂÃ]",
        "E": "[eéèëêEÉÈËÊ]",
        "I": "[iíìïîIÍÌÏÎ]",
        "O": "[oóòöôõOÓÒÖÔÕ]",
        "U": "[uúùüûUÚÙÜÛ]",
        "Ñ": "[nñNÑ]",
        "C": "[cçCÇ]",
    }
    return classes.get(char, re.escape(char))


def _extract_tokens(name: str) -> set[str]:
    """Extract individual tokens from a name (≥3 chars, excluding connectors).

    Only extracts tokens before the first connector word to avoid scrubbing
    words in patronymic/compound parts (e.g., "MARIA DE LOURDES" → only "MARIA").
    """
    tokens = set()
    words = name.strip().split()

    # Extract tokens only up to the first connector word
    for word in words:
        if word.lower() in _CONNECTORS:
            # Stop extraction at first connector
            break
        if len(word) >= 3:
            tokens.add(_strip_accents(word.upper()))

    return tokens
