"""Rows ready to be typed into the HR tool."""

from collections.abc import Sequence

from tabernas.domain.types import (
    AttendanceWarning,
    DayResult,
    Employee,
    Outcome,
    RhRow,
    RhType,
    WarningCode,
)


def rh_type_for(result: DayResult) -> RhType | None:
    justified = result.justification_id is not None
    if result.outcome == Outcome.LATE:
        return result.rh_type if justified else RhType.RETARDO
    if result.outcome == Outcome.ABSENT:
        return result.rh_type if justified else RhType.FALTA_INJUSTIFICADA
    if result.outcome == Outcome.JUSTIFIED:
        return result.rh_type
    return None


def to_rh_rows(
    results: Sequence[DayResult], employees: Sequence[Employee]
) -> tuple[list[RhRow], list[AttendanceWarning]]:
    by_id = {e.id: e for e in employees}
    typed = [(r, rh_type_for(r)) for r in results]
    rows = [
        RhRow(
            employee_id=r.employee_id,
            name=by_id[r.employee_id].rh_name or by_id[r.employee_id].short_name,
            day=r.day,
            rh_type=rh_type,
            comment=r.comment,
        )
        for r, rh_type in typed
        if rh_type is not None and rh_type != RhType.NO_CAPTURAR
    ]
    missing = sorted({row.employee_id for row in rows if not by_id[row.employee_id].rh_name})
    warnings = [
        AttendanceWarning(
            WarningCode.MISSING_RH_NAME,
            employee_id,
            None,
            f"{by_id[employee_id].short_name} no tiene nombre en RH",
        )
        for employee_id in missing
    ]
    return sorted(rows, key=lambda row: (row.name, row.day)), warnings
