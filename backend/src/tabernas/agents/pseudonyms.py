"""Pseudonyms (spec E4): Claude only ever sees E{id}, never an employee's name."""

import re
from collections.abc import Iterable, Sequence

from tabernas.domain.types import Employee

_ALIAS = re.compile(r"E(\d+)")
_ALIAS_TOKEN = re.compile(r"\{(E\d+)\}")


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
    index = _name_index(employees)
    pattern = _name_pattern(index)
    if pattern is None:
        return text
    return pattern.sub(lambda m: alias(index[m.group(1).casefold()]), text)


def contains_known_name(text: str, employees: Sequence[Employee]) -> bool:
    pattern = _name_pattern(_name_index(employees))
    return pattern is not None and pattern.search(_ALIAS_TOKEN.sub(" ", text)) is not None


def _name_index(employees: Sequence[Employee]) -> dict[str, int]:
    index: dict[str, int] = {}
    for employee in employees:
        for name in (employee.short_name, employee.rh_name):
            if name and name.strip():
                index.setdefault(name.strip().casefold(), employee.id)
    return index


def _name_pattern(names: Iterable[str]) -> re.Pattern[str] | None:
    ordered = sorted(names, key=len, reverse=True)  # longest first: "ANA MARIA" before "ANA"
    if not ordered:
        return None
    alternatives = "|".join(re.escape(name) for name in ordered)
    return re.compile(rf"(?<!\w)({alternatives})(?!\w)", re.IGNORECASE)
