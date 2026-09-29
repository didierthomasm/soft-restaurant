from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import JustificationRow
from tabernas.domain.justify import default_rh_type
from tabernas.domain.types import Incident, Justification, RhType
from tabernas.domain.validation import validate_justification
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset({"reason", "rh_type"})


def to_justification(row: JustificationRow) -> Justification:
    return Justification(
        id=row.id,
        employee_id=row.employee_id,
        day=row.day,
        incident=row.incident,
        reason=row.reason,
        rh_type=row.rh_type,
    )


class JustificationRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(
        self, *, start: date, end: date, employee_id: int | None = None
    ) -> list[Justification]:
        stmt = (
            select(JustificationRow)
            .where(JustificationRow.day >= start, JustificationRow.day <= end)
            .order_by(JustificationRow.day, JustificationRow.id)
        )
        if employee_id is not None:
            stmt = stmt.where(JustificationRow.employee_id == employee_id)
        return [to_justification(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, justification_id: int) -> Justification:
        return to_justification(self._require(justification_id))

    def create(
        self,
        *,
        employee_id: int,
        day: date,
        incident: Incident,
        reason: str,
        rh_type: RhType | None = None,
    ) -> Justification:
        chosen = rh_type or default_rh_type(incident)
        validate_justification(incident=incident, rh_type=chosen)
        require_employee(self._session, employee_id)
        row = JustificationRow(
            employee_id=employee_id, day=day, incident=incident, reason=reason, rh_type=chosen
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError("Esa incidencia ya tiene justificación") from exc
        return to_justification(row)

    def update(self, justification_id: int, changes: Mapping[str, Any]) -> Justification:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(justification_id)
        if "rh_type" in changes:
            validate_justification(incident=row.incident, rh_type=changes["rh_type"])
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_justification(row)

    def delete(self, justification_id: int) -> None:
        self._session.delete(self._require(justification_id))
        self._session.flush()

    def _require(self, justification_id: int) -> JustificationRow:
        row = self._session.get(JustificationRow, justification_id)
        if row is None:
            raise NotFoundError("Justificación no encontrada")
        return row
