"""Synthetic employees and rest rules matching FakeSource. Only for SR_MODE=fake."""

from datetime import date

from sqlalchemy.orm import Session

from tabernas.domain.types import Employee
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.sr.fake_source import FAKE_DOUBLE_REST_ANCHOR, FAKE_EMPLOYEES

DEMO_RULES_VALID_FROM = date(2024, 1, 1)
FAKE_SR_IDS = frozenset(fake.sr_id for fake in FAKE_EMPLOYEES)


def _refuse_if_real_employees_present(employees: EmployeeRepo) -> None:
    if any(e.sr_id not in FAKE_SR_IDS for e in employees.find_all()):
        raise DomainValidationError("La base ya tiene empleados reales; no se mezclan datos demo")


def seed_demo_data(session: Session) -> list[Employee]:
    employees = EmployeeRepo(session)
    _refuse_if_real_employees_present(employees)
    rules = RestRuleRepo(session)
    existing = employees.existing_sr_ids()
    created: list[Employee] = []
    for fake in FAKE_EMPLOYEES:
        if fake.sr_id in existing:
            continue
        employee = employees.create(
            sr_id=fake.sr_id,
            short_name=fake.name,
            rh_name=f"{fake.name} (RH)",
            area=fake.area,
            applies_lateness=fake.checks_in,
            tracks_attendance=fake.checks_in,
        )
        rules.create(
            employee_id=employee.id,
            fixed_weekday=fake.fixed_rest,
            extra_weekday=fake.extra_rest,
            double_rest_anchor=FAKE_DOUBLE_REST_ANCHOR,
            valid_from=DEMO_RULES_VALID_FROM,
            valid_to=None,
        )
        created.append(employee)
    return created
