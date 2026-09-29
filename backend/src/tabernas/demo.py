"""Synthetic employees and rest rules matching FakeSource. Only for SR_MODE=fake."""

from datetime import date

from sqlalchemy.orm import Session

from tabernas.domain.types import Employee
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.sr.fake_source import FAKE_DOUBLE_REST_ANCHOR, FAKE_EMPLOYEES

DEMO_RULES_VALID_FROM = date(2024, 1, 1)


def seed_demo_data(session: Session) -> list[Employee]:
    employees = EmployeeRepo(session)
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
