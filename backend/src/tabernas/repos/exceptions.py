from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import ScheduleExceptionRow
from tabernas.domain.types import ExceptionKind, RhType, ScheduleException
from tabernas.domain.validation import DomainValidationError, validate_exception
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset({"date_from", "date_to", "rh_type", "comment"})
_VALIDATED_FIELDS = ("kind", "employee_id", "date_from", "date_to", "rh_type")


def to_exception(row: ScheduleExceptionRow) -> ScheduleException:
    return ScheduleException(
        id=row.id,
        kind=row.kind,
        employee_id=row.employee_id,
        date_from=row.date_from,
        date_to=row.date_to,
        rh_type=row.rh_type,
        comment=row.comment,
    )


class ExceptionRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
        employee_id: int | None = None,
    ) -> list[ScheduleException]:
        stmt = select(ScheduleExceptionRow).order_by(
            ScheduleExceptionRow.date_from, ScheduleExceptionRow.id
        )
        if start is not None:
            stmt = stmt.where(ScheduleExceptionRow.date_to >= start)
        if end is not None:
            stmt = stmt.where(ScheduleExceptionRow.date_from <= end)
        if employee_id is not None:
            stmt = stmt.where(ScheduleExceptionRow.employee_id == employee_id)
        return [to_exception(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, exception_id: int) -> ScheduleException:
        return to_exception(self._require(exception_id))

    def create(
        self,
        *,
        kind: ExceptionKind,
        employee_id: int | None,
        date_from: date,
        date_to: date,
        rh_type: RhType | None,
        comment: str,
    ) -> ScheduleException:
        fields: dict[str, Any] = {
            "kind": kind,
            "employee_id": employee_id,
            "date_from": date_from,
            "date_to": date_to,
            "rh_type": rh_type,
        }
        self._validate(fields, exclude_id=None)
        row = ScheduleExceptionRow(**fields, comment=comment)
        self._session.add(row)
        self._session.flush()
        return to_exception(row)

    def update(self, exception_id: int, changes: Mapping[str, Any]) -> ScheduleException:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(exception_id)
        current = {field: getattr(row, field) for field in _VALIDATED_FIELDS}
        validated = {k: v for k, v in changes.items() if k != "comment"}
        self._validate({**current, **validated}, exclude_id=exception_id)
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_exception(row)

    def delete(self, exception_id: int) -> None:
        self._session.delete(self._require(exception_id))
        self._session.flush()

    def create_rest_swap(
        self, *, employee_id: int, absent_day: date, worked_day: date, comment: str
    ) -> tuple[ScheduleException, ScheduleException]:
        """Decision #4: incident on the day not worked; a rest day becomes a workday."""
        if absent_day == worked_day:
            raise DomainValidationError("El día de descanso y el día trabajado deben ser distintos")
        with self._session.begin_nested():
            absence = self.create(
                kind=ExceptionKind.WORK_TO_ABSENCE,
                employee_id=employee_id,
                date_from=absent_day,
                date_to=absent_day,
                rh_type=RhType.DESCANSO,
                comment=comment,
            )
            worked = self.create(
                kind=ExceptionKind.REST_TO_WORK,
                employee_id=employee_id,
                date_from=worked_day,
                date_to=worked_day,
                rh_type=None,
                comment=comment,
            )
        return absence, worked

    def _require(self, exception_id: int) -> ScheduleExceptionRow:
        row = self._session.get(ScheduleExceptionRow, exception_id)
        if row is None:
            raise NotFoundError("Excepción no encontrada")
        return row

    def _validate(self, fields: Mapping[str, Any], exclude_id: int | None) -> None:
        validate_exception(**fields)
        employee_id = fields["employee_id"]
        if employee_id is None:
            return
        require_employee(self._session, employee_id)
        clashing = [
            e
            for e in self.find_all(
                start=fields["date_from"], end=fields["date_to"], employee_id=employee_id
            )
            if e.id != exclude_id
        ]
        if clashing:
            raise ConflictError("Ya hay una excepción para ese empleado en esas fechas")
