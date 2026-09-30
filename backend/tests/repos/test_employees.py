import pytest
from sqlalchemy.orm import Session

from tabernas.domain.types import Area
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.errors import ConflictError, NotFoundError
from tests.repos.helpers import make_employee


def test_create_and_find(session: Session) -> None:
    created = make_employee(session, area=Area.KITCHEN)
    assert created.active
    assert EmployeeRepo(session).find_by_id(created.id) == created


def test_find_all_orders_by_name_and_filters_active(session: Session) -> None:
    repo = EmployeeRepo(session)
    b = make_employee(session, 102, short_name="EMPLEADO B")
    a = make_employee(session, 101, short_name="EMPLEADO A")
    repo.update(b.id, {"active": False})
    assert [e.id for e in repo.find_all()] == [a.id, b.id]
    assert [e.id for e in repo.find_all(active_only=True)] == [a.id]


def test_duplicate_sr_id_conflicts_and_session_stays_usable(session: Session) -> None:
    make_employee(session, 101)
    with pytest.raises(ConflictError, match="101"):
        make_employee(session, 101, short_name="OTRO")
    assert make_employee(session, 102).sr_id == 102


def test_employees_without_sr_id_can_repeat(session: Session) -> None:
    make_employee(session, None, short_name="GERENTE")
    make_employee(session, None, short_name="OTRO")
    assert len(EmployeeRepo(session).find_all()) == 2


def test_update_returns_new_object(session: Session) -> None:
    created = make_employee(session)
    updated = EmployeeRepo(session).update(created.id, {"rh_name": "APELLIDO NOMBRE"})
    assert updated.rh_name == "APELLIDO NOMBRE"
    assert created.rh_name is None


def test_update_rejects_non_editable_fields(session: Session) -> None:
    created = make_employee(session)
    with pytest.raises(DomainValidationError, match="sr_id"):
        EmployeeRepo(session).update(created.id, {"sr_id": 5})


def test_missing_employee_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        EmployeeRepo(session).find_by_id(999)


def test_existing_sr_ids(session: Session) -> None:
    make_employee(session, 101)
    make_employee(session, None, short_name="GERENTE")
    assert EmployeeRepo(session).existing_sr_ids() == {101}
