"""Read-only tools of the weekly-review agent (spec §5.2).

They answer from the ReviewContext computed by the service: no SR, no Postgres, no
writes. Employees appear only as E{id}; free text goes through scrub()."""

import json
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from tabernas.agents.pseudonyms import alias, parse_alias, scrub
from tabernas.domain.review_types import REVIEW_HISTORY_WEEKS, Finding, ReviewContext
from tabernas.domain.summary import Grouping, summarize
from tabernas.domain.types import DayResult, Outcome

INCIDENT_OUTCOMES = frozenset(
    {Outcome.LATE, Outcome.ABSENT, Outcome.UNREGISTERED_CHANGE, Outcome.JUSTIFIED}
)
WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_EMPLOYEE = {"type": "string", "description": "Seudónimo del empleado, p. ej. E12"}


class ToolError(ValueError):
    """Bad tool input. Sent back to Claude as an is_error tool_result."""


def _schema(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "get_week_findings",
        "description": "Hallazgos de la semana calculados por el sistema. Cada uno debe "
        "aparecer exactamente una vez en tu respuesta, con su id tal cual.",
        "input_schema": _schema({}),
        "strict": True,
    },
    {
        "name": "get_week_incidents",
        "description": "Incidencias de la semana (retardos, faltas, checadas en descanso, "
        "ausencias justificadas) y filas propuestas para capturar en RH.",
        "input_schema": _schema({}),
        "strict": True,
    },
    {
        "name": "get_employee_history",
        "description": "Resumen por semana de un empleado en las semanas anteriores a la "
        f"revisada (de 1 a {REVIEW_HISTORY_WEEKS}).",
        "input_schema": _schema(
            {"employee": _EMPLOYEE, "weeks": {"type": "integer", "description": "Semanas previas"}}
        ),
        "strict": True,
    },
    {
        "name": "get_employee_week",
        "description": "Día a día de un empleado en la semana revisada: lo planeado, el "
        "resultado, la hora de checada y comentarios.",
        "input_schema": _schema({"employee": _EMPLOYEE}),
        "strict": True,
    },
]


class ReviewTools:
    def __init__(self, context: ReviewContext) -> None:
        self._context = context
        self._employee_ids = {employee.id for employee in context.employees}

    def call(self, name: str, arguments: Mapping[str, Any]) -> str:
        handlers: dict[str, Callable[[], Any]] = {
            "get_week_findings": self._week_findings,
            "get_week_incidents": self._week_incidents,
            "get_employee_history": lambda: self._employee_history(
                self._employee(arguments), self._weeks(arguments)
            ),
            "get_employee_week": lambda: self._employee_week(self._employee(arguments)),
        }
        handler = handlers.get(name)
        if handler is None:
            raise ToolError(f"Herramienta desconocida: {name}")
        return json.dumps(handler(), ensure_ascii=False)

    def _week_findings(self) -> list[dict[str, Any]]:
        return [_finding_json(finding) for finding in self._context.findings]

    def _week_incidents(self) -> dict[str, Any]:
        incidents = [
            self._day_json(r) for r in self._context.week_results if r.outcome in INCIDENT_OUTCOMES
        ]
        rows = [
            {
                "employee": alias(row.employee_id),
                "day": row.day.isoformat(),
                "rh_type": row.rh_type.value,
                "comment": self._scrub(row.comment),
            }
            for row in self._context.rh_rows
        ]
        return {"incidents": incidents, "rh_rows": rows}

    def _employee_history(self, employee_id: int, weeks: int) -> list[dict[str, Any]]:
        start = self._context.start
        since = start - timedelta(weeks=weeks)
        results = [
            r
            for r in self._context.history_results
            if r.employee_id == employee_id and since <= r.day < start
        ]
        return [
            {
                "week": s.period,
                "worked": s.worked,
                "late": s.late,
                "late_justified": s.late_justified,
                "absent": s.absent,
                "absent_justified": s.absent_justified,
                "unresolved": s.unresolved,
            }
            for s in summarize(results, Grouping.WEEK)
        ]

    def _employee_week(self, employee_id: int) -> list[dict[str, Any]]:
        week = self._context.week_results
        return [self._day_json(r) for r in week if r.employee_id == employee_id]

    def _day_json(self, r: DayResult) -> dict[str, Any]:
        return {
            "employee": alias(r.employee_id),
            "day": r.day.isoformat(),
            "weekday": WEEKDAYS[r.day.weekday()],
            "planned": r.planned.value,
            "outcome": r.outcome.value,
            "checkin": r.checkin.strftime("%H:%M") if r.checkin else None,
            "minutes_late": r.minutes_late,
            "rh_type": r.rh_type.value if r.rh_type else None,
            "justified": r.justification_id is not None,
            "comment": self._scrub(r.comment),
        }

    def _scrub(self, text: str) -> str:
        return scrub(text, self._context.employees)

    def _employee(self, arguments: Mapping[str, Any]) -> int:
        raw = arguments.get("employee")
        employee_id = parse_alias(raw) if isinstance(raw, str) else None
        if employee_id is None or employee_id not in self._employee_ids:
            raise ToolError(f"Empleado desconocido: {raw!r}. Usa un seudónimo como E12.")
        return employee_id

    def _weeks(self, arguments: Mapping[str, Any]) -> int:
        weeks = arguments.get("weeks")
        error = ToolError(f"weeks debe ser un entero entre 1 y {REVIEW_HISTORY_WEEKS}")
        if isinstance(weeks, bool) or not isinstance(weeks, int):
            raise error
        if not 1 <= weeks <= REVIEW_HISTORY_WEEKS:
            raise error
        return weeks


def _finding_json(finding: Finding) -> dict[str, Any]:
    employee = alias(finding.employee_id) if finding.employee_id is not None else None
    return {
        "id": finding.id,
        "kind": finding.kind.value,
        "employee": employee,
        "days": [day.isoformat() for day in finding.days],
        "facts": dict(finding.facts),
    }
