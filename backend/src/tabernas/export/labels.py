"""Spanish labels and colors for user-facing exports."""

from tabernas.domain.types import Outcome, RhType

DAY_ABBR = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")

OUTCOME_LABELS: dict[Outcome, str] = {
    Outcome.OK: "A tiempo",
    Outcome.LATE: "Retardo",
    Outcome.ABSENT: "Falta",
    Outcome.UNREGISTERED_CHANGE: "Cambio sin registrar",
    Outcome.REST: "Descanso",
    Outcome.CLOSED: "Cerrado",
    Outcome.JUSTIFIED: "Justificado",
    Outcome.PENDING: "Pendiente",
    Outcome.FUTURE: "",
}

OUTCOME_FILLS: dict[Outcome, str] = {
    Outcome.OK: "E6F4EA",
    Outcome.LATE: "FFF4CE",
    Outcome.ABSENT: "FDE2E1",
    Outcome.UNREGISTERED_CHANGE: "E8DEF8",
    Outcome.REST: "F1F3F4",
    Outcome.CLOSED: "DADCE0",
    Outcome.JUSTIFIED: "E3F2FD",
    Outcome.PENDING: "FFFFFF",
    Outcome.FUTURE: "FFFFFF",
}

RH_LABELS: dict[RhType, str] = {
    RhType.RETARDO: "Retardo",
    RhType.FALTA_INJUSTIFICADA: "Falta injustificada",
    RhType.FALTA_JUSTIFICADA: "Falta justificada",
    RhType.VACACIONES: "Vacaciones",
    RhType.INCAPACIDAD: "Incapacidad",
    RhType.PERMISO: "Permiso",
    RhType.DESCANSO: "Descanso",
    RhType.NO_CAPTURAR: "No se captura",
}
