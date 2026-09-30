"""Employee persistence. Returns immutable domain objects, never ORM rows."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import EmployeeRow
from tabernas.domain.types import Area, Employee
from tabernas.repos.common import check_fields, require_employee
from tabernas.repos.errors import ConflictError

EDITABLE_FIELDS = frozenset(
    {"short_name", "rh_name", "area", "applies_lateness", "tracks_attendance", "active"}
)


def to_employee(row: EmployeeRow) -> Employee:
    return Employee(
        id=row.id,
        sr_id=row.sr_id,
        short_name=row.short_name,
        rh_name=row.rh_name,
        area=row.area,
        applies_lateness=row.applies_lateness,
        tracks_attendance=row.tracks_attendance,
        active=row.active,
    )


class EmployeeRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(self, *, active_only: bool = False) -> list[Employee]:
        stmt = select(EmployeeRow).order_by(EmployeeRow.short_name, EmployeeRow.id)
        if active_only:
            stmt = stmt.where(EmployeeRow.active.is_(True))
        return [to_employee(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, employee_id: int) -> Employee:
        return to_employee(require_employee(self._session, employee_id))

    def existing_sr_ids(self) -> set[int]:
        ids = self._session.scalars(select(EmployeeRow.sr_id))
        return {sr_id for sr_id in ids if sr_id is not None}

    def create(
        self,
        *,
        sr_id: int | None,
        short_name: str,
        rh_name: str | None,
        area: Area,
        applies_lateness: bool,
        tracks_attendance: bool,
    ) -> Employee:
        row = EmployeeRow(
            sr_id=sr_id,
            short_name=short_name,
            rh_name=rh_name,
            area=area,
            applies_lateness=applies_lateness,
            tracks_attendance=tracks_attendance,
            active=True,
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError(f"Ya existe un empleado con id SR {sr_id}") from exc
        return to_employee(row)

    def update(self, employee_id: int, changes: Mapping[str, object]) -> Employee:
        check_fields(changes, EDITABLE_FIELDS)
        row = require_employee(self._session, employee_id)
        for field, value in changes.items():
            setattr(row, field, value)  # ORM rows are the mutable persistence boundary
        self._session.flush()
        return to_employee(row)
