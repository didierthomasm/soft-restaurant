from collections.abc import Collection, Mapping
from datetime import date

from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import NotFoundError


def require_employee(session: Session, employee_id: int) -> EmployeeRow:
    row = session.get(EmployeeRow, employee_id)
    if row is None:
        raise NotFoundError("Empleado no encontrado")
    return row


def ranges_overlap(a_from: date, a_to: date | None, b_from: date, b_to: date | None) -> bool:
    return a_from <= (b_to or date.max) and b_from <= (a_to or date.max)


def check_fields(changes: Mapping[str, object], editable: Collection[str]) -> None:
    unknown = sorted(set(changes) - set(editable))
    if unknown:
        raise DomainValidationError(f"Campos no editables: {', '.join(unknown)}")
