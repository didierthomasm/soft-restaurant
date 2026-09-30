"""Attach the manager's justifications to late/absent results."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date

from tabernas.domain.types import (
    AttendanceWarning,
    DayResult,
    Incident,
    Justification,
    Outcome,
    RhType,
    WarningCode,
)

_DEFAULT_RH_TYPE = {Incident.LATE: RhType.NO_CAPTURAR, Incident.ABSENT: RhType.FALTA_JUSTIFICADA}
_INCIDENT_BY_OUTCOME = {Outcome.LATE: Incident.LATE, Outcome.ABSENT: Incident.ABSENT}

Key = tuple[int, date, Incident]


def default_rh_type(incident: Incident) -> RhType:
    return _DEFAULT_RH_TYPE[incident]


def apply_justifications(
    results: Sequence[DayResult], justifications: Sequence[Justification]
) -> tuple[list[DayResult], list[AttendanceWarning]]:
    by_key = {(j.employee_id, j.day, j.incident): j for j in justifications}
    applied = [_apply(r, by_key) for r in results]
    incidents = {
        (r.employee_id, r.day, _INCIDENT_BY_OUTCOME[r.outcome])
        for r in results
        if r.outcome in _INCIDENT_BY_OUTCOME
    }
    warnings = [
        AttendanceWarning(
            WarningCode.ORPHAN_JUSTIFICATION,
            j.employee_id,
            j.day,
            f"Justificación de {j.incident} sin incidencia correspondiente",
        )
        for j in justifications
        if (j.employee_id, j.day, j.incident) not in incidents
    ]
    return applied, warnings


def _apply(result: DayResult, by_key: Mapping[Key, Justification]) -> DayResult:
    incident = _INCIDENT_BY_OUTCOME.get(result.outcome)
    if incident is None:
        return result
    found = by_key.get((result.employee_id, result.day, incident))
    if found is None:
        return result
    return replace(result, justification_id=found.id, rh_type=found.rh_type, comment=found.reason)
