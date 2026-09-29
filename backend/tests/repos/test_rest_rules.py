from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.rest_rules import RestRuleRepo
from tests.repos.helpers import make_employee

MONDAY = date(2026, 9, 28)


def create(
    session: Session,
    employee_id: int,
    *,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    anchor: date = MONDAY,
):
    return RestRuleRepo(session).create(
        employee_id=employee_id,
        fixed_weekday=1,
        extra_weekday=0,
        double_rest_anchor=anchor,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def test_create_and_find(session: Session) -> None:
    employee = make_employee(session)
    rule = create(session, employee.id)
    repo = RestRuleRepo(session)
    assert repo.find_by_id(rule.id) == rule
    assert repo.find_all(employee_id=employee.id) == [rule]


def test_unknown_employee_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        create(session, 999)


def test_invalid_rule_is_rejected(session: Session) -> None:
    employee = make_employee(session)
    with pytest.raises(DomainValidationError, match="lunes"):
        create(session, employee.id, anchor=date(2026, 9, 29))


def test_overlapping_validity_conflicts(session: Session) -> None:
    employee = make_employee(session)
    create(session, employee.id)
    with pytest.raises(ConflictError, match="traslapa"):
        create(session, employee.id, valid_from=date(2026, 10, 1))


def test_consecutive_rules_and_other_employees_do_not_conflict(session: Session) -> None:
    a = make_employee(session, 101)
    b = make_employee(session, 102, short_name="EMPLEADO B")
    first = create(session, a.id, valid_to=date(2026, 9, 30))
    create(session, a.id, valid_from=date(2026, 10, 1))
    create(session, b.id)
    assert len(RestRuleRepo(session).find_all()) == 3
    assert first.valid_to == date(2026, 9, 30)


def test_update_is_validated_against_other_rules(session: Session) -> None:
    employee = make_employee(session)
    first = create(session, employee.id, valid_to=date(2026, 9, 30))
    create(session, employee.id, valid_from=date(2026, 10, 1))
    repo = RestRuleRepo(session)
    with pytest.raises(ConflictError):
        repo.update(first.id, {"valid_to": None})
    assert repo.update(first.id, {"fixed_weekday": 3}).fixed_weekday == 3


def test_delete(session: Session) -> None:
    employee = make_employee(session)
    rule = create(session, employee.id)
    repo = RestRuleRepo(session)
    repo.delete(rule.id)
    with pytest.raises(NotFoundError):
        repo.find_by_id(rule.id)
