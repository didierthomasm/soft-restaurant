from datetime import date

import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import Incident, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.justifications import JustificationRepo
from tests.repos.helpers import make_employee

DAY = date(2026, 9, 23)


def test_create_uses_default_rh_type(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    late = repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Tráfico")
    absent = repo.create(
        employee_id=employee.id, day=DAY, incident=Incident.ABSENT, reason="Enfermo"
    )
    assert late.rh_type == RhType.NO_CAPTURAR
    assert absent.rh_type == RhType.FALTA_JUSTIFICADA


def test_duplicate_conflicts(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Tráfico")
    with pytest.raises(ConflictError):
        repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="Otra")


def test_rh_type_is_validated_on_create_and_update(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    with pytest.raises(DomainValidationError):
        repo.create(
            employee_id=employee.id,
            day=DAY,
            incident=Incident.LATE,
            reason="x",
            rh_type=RhType.VACACIONES,
        )
    created = repo.create(employee_id=employee.id, day=DAY, incident=Incident.ABSENT, reason="x")
    assert repo.update(created.id, {"rh_type": RhType.INCAPACIDAD}).rh_type == RhType.INCAPACIDAD
    with pytest.raises(DomainValidationError):
        repo.update(created.id, {"rh_type": RhType.RETARDO})


def test_find_all_by_range_and_delete(session: Session) -> None:
    employee = make_employee(session)
    repo = JustificationRepo(session)
    inside = repo.create(employee_id=employee.id, day=DAY, incident=Incident.LATE, reason="x")
    repo.create(employee_id=employee.id, day=date(2026, 9, 30), incident=Incident.LATE, reason="y")
    assert repo.find_all(start=date(2026, 9, 21), end=date(2026, 9, 27)) == [inside]
    repo.delete(inside.id)
    with pytest.raises(NotFoundError):
        repo.find_by_id(inside.id)
