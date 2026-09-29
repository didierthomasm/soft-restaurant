from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import RestRuleRow
from tabernas.domain.types import RestRule
from tabernas.domain.validation import validate_rest_rule
from tabernas.repos.common import check_fields, ranges_overlap, require_employee
from tabernas.repos.errors import ConflictError, NotFoundError

EDITABLE_FIELDS = frozenset(
    {"fixed_weekday", "extra_weekday", "double_rest_anchor", "valid_from", "valid_to"}
)


def to_rest_rule(row: RestRuleRow) -> RestRule:
    return RestRule(
        id=row.id,
        employee_id=row.employee_id,
        fixed_weekday=row.fixed_weekday,
        extra_weekday=row.extra_weekday,
        double_rest_anchor=row.double_rest_anchor,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def _fields_of(row: RestRuleRow) -> dict[str, Any]:
    return {field: getattr(row, field) for field in EDITABLE_FIELDS}


class RestRuleRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_all(self, *, employee_id: int | None = None) -> list[RestRule]:
        stmt = select(RestRuleRow).order_by(RestRuleRow.employee_id, RestRuleRow.valid_from)
        if employee_id is not None:
            stmt = stmt.where(RestRuleRow.employee_id == employee_id)
        return [to_rest_rule(row) for row in self._session.scalars(stmt)]

    def find_by_id(self, rule_id: int) -> RestRule:
        return to_rest_rule(self._require(rule_id))

    def create(
        self,
        *,
        employee_id: int,
        fixed_weekday: int,
        extra_weekday: int,
        double_rest_anchor: date,
        valid_from: date,
        valid_to: date | None,
    ) -> RestRule:
        require_employee(self._session, employee_id)
        fields: dict[str, Any] = {
            "fixed_weekday": fixed_weekday,
            "extra_weekday": extra_weekday,
            "double_rest_anchor": double_rest_anchor,
            "valid_from": valid_from,
            "valid_to": valid_to,
        }
        self._validate(employee_id, fields, exclude_id=None)
        row = RestRuleRow(employee_id=employee_id, **fields)
        self._session.add(row)
        self._session.flush()
        return to_rest_rule(row)

    def update(self, rule_id: int, changes: Mapping[str, Any]) -> RestRule:
        check_fields(changes, EDITABLE_FIELDS)
        row = self._require(rule_id)
        self._validate(row.employee_id, {**_fields_of(row), **changes}, exclude_id=rule_id)
        for field, value in changes.items():
            setattr(row, field, value)
        self._session.flush()
        return to_rest_rule(row)

    def delete(self, rule_id: int) -> None:
        self._session.delete(self._require(rule_id))
        self._session.flush()

    def _require(self, rule_id: int) -> RestRuleRow:
        row = self._session.get(RestRuleRow, rule_id)
        if row is None:
            raise NotFoundError("Regla de descanso no encontrada")
        return row

    def _validate(
        self, employee_id: int, fields: Mapping[str, Any], exclude_id: int | None
    ) -> None:
        validate_rest_rule(**fields)
        others = [r for r in self.find_all(employee_id=employee_id) if r.id != exclude_id]
        if any(
            ranges_overlap(fields["valid_from"], fields["valid_to"], o.valid_from, o.valid_to)
            for o in others
        ):
            raise ConflictError("La vigencia se traslapa con otra regla del mismo empleado")
