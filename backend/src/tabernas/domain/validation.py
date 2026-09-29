"""Validation rules shared by repositories and the API. Raise DomainValidationError."""

from datetime import date, time

from tabernas.domain.types import ExceptionKind, Incident, RhType


class DomainValidationError(ValueError):
    """Input the user can fix. The API maps it to 422 with this message."""


ABSENCE_RH_TYPES = frozenset(
    {
        RhType.FALTA_JUSTIFICADA,
        RhType.VACACIONES,
        RhType.INCAPACIDAD,
        RhType.PERMISO,
        RhType.DESCANSO,
    }
)
JUSTIFICATION_RH_TYPES = {
    Incident.LATE: frozenset({RhType.NO_CAPTURAR, RhType.RETARDO}),
    Incident.ABSENT: ABSENCE_RH_TYPES | {RhType.NO_CAPTURAR},
}
MAX_TOLERANCE_MINUTES = 60


def validate_rest_rule(
    *,
    fixed_weekday: int,
    extra_weekday: int,
    double_rest_anchor: date,
    valid_from: date,
    valid_to: date | None,
) -> None:
    for label, value in (("día fijo", fixed_weekday), ("día extra", extra_weekday)):
        if not 0 <= value <= 6:
            raise DomainValidationError(f"El {label} debe estar entre 0 (lunes) y 6 (domingo)")
    if fixed_weekday == extra_weekday:
        raise DomainValidationError("El día fijo y el día extra deben ser distintos")
    if double_rest_anchor.weekday() != 0:
        raise DomainValidationError("La semana de descanso doble se indica con un lunes")
    if valid_to is not None and valid_to < valid_from:
        raise DomainValidationError("La vigencia termina antes de empezar")


def validate_exception(
    *,
    kind: ExceptionKind,
    employee_id: int | None,
    rh_type: RhType | None,
    date_from: date,
    date_to: date,
) -> None:
    if date_to < date_from:
        raise DomainValidationError("La fecha final es anterior a la inicial")
    if (kind == ExceptionKind.STORE_CLOSED) != (employee_id is None):
        raise DomainValidationError(
            "El cierre del local aplica a todos; las demás excepciones requieren empleado"
        )
    if kind == ExceptionKind.WORK_TO_ABSENCE:
        if rh_type not in ABSENCE_RH_TYPES:
            raise DomainValidationError("Indica el tipo de ausencia para RH")
    elif rh_type is not None:
        raise DomainValidationError("Solo las ausencias llevan tipo de RH")


def validate_justification(*, incident: Incident, rh_type: RhType) -> None:
    if rh_type not in JUSTIFICATION_RH_TYPES[incident]:
        raise DomainValidationError("Tipo de RH no válido para esta incidencia")


def parse_hhmm(value: str) -> time:
    error = DomainValidationError(f"Hora inválida: {value!r} (usa HH:MM)")
    if len(value) != 5 or value[2] != ":":
        raise error
    try:
        return time(int(value[:2]), int(value[3:]))
    except ValueError as exc:
        raise error from exc


def format_hhmm(value: time) -> str:
    return value.strftime("%H:%M")


def validate_tolerance(minutes: int) -> None:
    if not 0 <= minutes <= MAX_TOLERANCE_MINUTES:
        raise DomainValidationError(
            f"La tolerancia debe estar entre 0 y {MAX_TOLERANCE_MINUTES} minutos"
        )
