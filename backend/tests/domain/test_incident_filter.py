from datetime import date

import pytest

from tabernas.domain.incident_filter import (
    DEFAULT_PAGE_SIZE,
    INCIDENT_OUTCOMES,
    IncidentFilter,
    IncidentStatus,
    IncidentType,
    PageRequest,
    count_unresolved,
    filter_incidents,
    paginate,
)
from tabernas.domain.types import Outcome
from tabernas.domain.validation import DomainValidationError
from tests.domain.factories import result

OK_1 = result(Outcome.OK, employee_id=1, day=date(2026, 9, 21))
REST_2 = result(Outcome.REST, employee_id=2, day=date(2026, 9, 22))
LATE_1 = result(Outcome.LATE, employee_id=1)
LATE_2_JUSTIFIED = result(Outcome.LATE, employee_id=2, justification_id=9)
ABSENT_1 = result(Outcome.ABSENT, employee_id=1, day=date(2026, 9, 24))
CHANGE_2 = result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=date(2026, 9, 25))
VACATION_1 = result(Outcome.JUSTIFIED, employee_id=1, day=date(2026, 9, 26))
ALL = [OK_1, REST_2, LATE_1, LATE_2_JUSTIFIED, ABSENT_1, CHANGE_2, VACATION_1]


def test_incident_types_are_the_incident_outcomes() -> None:
    assert {Outcome(t.value) for t in IncidentType} == INCIDENT_OUTCOMES


def test_default_filter_keeps_only_incidents_in_input_order() -> None:
    assert filter_incidents(ALL, IncidentFilter()) == [
        LATE_1,
        LATE_2_JUSTIFIED,
        ABSENT_1,
        CHANGE_2,
        VACATION_1,
    ]


def test_filter_by_employee() -> None:
    assert filter_incidents(ALL, IncidentFilter(employee_id=2)) == [LATE_2_JUSTIFIED, CHANGE_2]


def test_filter_by_types() -> None:
    types = frozenset({IncidentType.LATE, IncidentType.JUSTIFIED})
    assert filter_incidents(ALL, IncidentFilter(types=types)) == [
        LATE_1,
        LATE_2_JUSTIFIED,
        VACATION_1,
    ]


def test_justified_status_includes_justifications_and_exception_absences() -> None:
    found = filter_incidents(ALL, IncidentFilter(status=IncidentStatus.JUSTIFIED))
    assert found == [LATE_2_JUSTIFIED, VACATION_1]


def test_unjustified_status_includes_unregistered_changes() -> None:
    found = filter_incidents(ALL, IncidentFilter(status=IncidentStatus.UNJUSTIFIED))
    assert found == [LATE_1, ABSENT_1, CHANGE_2]


def test_filters_combine() -> None:
    combined = IncidentFilter(
        employee_id=1,
        types=frozenset({IncidentType.LATE, IncidentType.ABSENT}),
        status=IncidentStatus.UNJUSTIFIED,
    )
    assert filter_incidents(ALL, combined) == [LATE_1, ABSENT_1]


def test_count_unresolved_respects_only_the_employee() -> None:
    assert count_unresolved(ALL, None) == 1
    assert count_unresolved(ALL, 2) == 1
    assert count_unresolved(ALL, 1) == 0


@pytest.mark.parametrize(("page", "expected"), [(1, [0, 1]), (2, [2, 3]), (3, [4]), (4, [])])
def test_paginate_slices_and_reports_the_real_total(page: int, expected: list[int]) -> None:
    found = paginate(list(range(5)), PageRequest(page=page, limit=2))
    assert (list(found.items), found.total, found.page, found.limit) == (expected, 5, page, 2)


def test_paginate_empty_uses_the_default_size() -> None:
    found = paginate([], PageRequest())
    assert (found.items, found.total, found.page, found.limit) == ((), 0, 1, DEFAULT_PAGE_SIZE)


@pytest.mark.parametrize("bad", [PageRequest(page=0), PageRequest(limit=0), PageRequest(limit=101)])
def test_paginate_rejects_bad_requests(bad: PageRequest) -> None:
    with pytest.raises(DomainValidationError):
        paginate([1], bad)
