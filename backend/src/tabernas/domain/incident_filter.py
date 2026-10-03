"""Filters and pages the incident list. Pure: no database, no HTTP."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from tabernas.domain.types import DayResult, Outcome
from tabernas.domain.validation import DomainValidationError

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class IncidentType(StrEnum):
    """The outcomes that count as incidents (same values as `Outcome`)."""

    LATE = "LATE"
    ABSENT = "ABSENT"
    UNREGISTERED_CHANGE = "UNREGISTERED_CHANGE"
    JUSTIFIED = "JUSTIFIED"


INCIDENT_OUTCOMES = frozenset(Outcome(t.value) for t in IncidentType)


class IncidentStatus(StrEnum):
    ALL = "all"
    JUSTIFIED = "justified"
    UNJUSTIFIED = "unjustified"


@dataclass(frozen=True)
class IncidentFilter:
    employee_id: int | None = None
    types: frozenset[IncidentType] = frozenset()  # empty = every type
    status: IncidentStatus = IncidentStatus.ALL


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    limit: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class Page[T]:
    items: tuple[T, ...]
    total: int
    page: int
    limit: int


def is_justified(result: DayResult) -> bool:
    return result.justification_id is not None or result.outcome == Outcome.JUSTIFIED


def _matches(result: DayResult, incident_filter: IncidentFilter) -> bool:
    if incident_filter.employee_id not in (None, result.employee_id):
        return False
    if incident_filter.types and IncidentType(result.outcome.value) not in incident_filter.types:
        return False
    if incident_filter.status == IncidentStatus.ALL:
        return True
    return is_justified(result) == (incident_filter.status == IncidentStatus.JUSTIFIED)


def filter_incidents(
    results: Sequence[DayResult], incident_filter: IncidentFilter
) -> list[DayResult]:
    return [r for r in results if r.outcome in INCIDENT_OUTCOMES and _matches(r, incident_filter)]


def count_unresolved(results: Sequence[DayResult], employee_id: int | None) -> int:
    """Unregistered changes of the range; ignores the type and status filters on purpose."""
    only_changes = IncidentFilter(
        employee_id=employee_id, types=frozenset({IncidentType.UNREGISTERED_CHANGE})
    )
    return len(filter_incidents(results, only_changes))


def paginate[T](items: Sequence[T], request: PageRequest) -> Page[T]:
    if request.page < 1:
        raise DomainValidationError("La página empieza en 1")
    if not 1 <= request.limit <= MAX_PAGE_SIZE:
        raise DomainValidationError(f"El tamaño de página va de 1 a {MAX_PAGE_SIZE}")
    start = (request.page - 1) * request.limit
    return Page(
        items=tuple(items[start : start + request.limit]),
        total=len(items),
        page=request.page,
        limit=request.limit,
    )
