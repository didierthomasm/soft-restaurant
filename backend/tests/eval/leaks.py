"""Leak detection for the live eval: at least as strict as pseudonyms.scrub()."""

import re
import unicodedata
from collections.abc import Sequence

from tabernas.agents.pseudonyms import contains_known_name
from tabernas.domain.types import Employee

CONNECTORS = frozenset({"de", "del", "la", "las", "los", "san", "y"})
MIN_PART = 3


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def _name_parts(employee: Employee) -> set[str]:
    parts: set[str] = set()
    for name in (employee.short_name, employee.rh_name):
        for word in re.findall(r"[^\W\d_]+", _fold(name or "")):
            if len(word) >= MIN_PART and word not in CONNECTORS:
                parts.add(word)
    return parts


def leaked_names(payload: str, employees: Sequence[Employee]) -> list[str]:
    """Names (whole, or any part of 3+ letters) found in payload; empty means clean."""
    found: list[str] = []
    if contains_known_name(payload, employees):
        found.append("<nombre completo>")
    folded = _fold(payload)
    for employee in employees:
        for part in sorted(_name_parts(employee)):
            if re.search(rf"(?<![^\W\d_]){re.escape(part)}(?![^\W\d_])", folded):
                found.append(part)
    return found
