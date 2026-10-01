"""Synthetic weeks with expected agent behavior (spec §10.2). No real data."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import date, datetime

from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import AttendanceWarning, DayResult, Outcome, WarningCode
from tests.agents.helpers import make_context
from tests.domain.factories import result

MON, TUE, WED, THU, FRI = (date(2026, 9, d) for d in (21, 22, 23, 24, 25))
JUSTIFY_OR_EXCEPTION = frozenset({SuggestedAction.JUSTIFY, SuggestedAction.ADD_EXCEPTION})


@dataclass(frozen=True)
class Scenario:
    name: str
    context: ReviewContext
    expected_high: frozenset[FindingKind] = frozenset()
    expected_actions: Mapping[FindingKind, frozenset[SuggestedAction]] = field(default_factory=dict)


def _ok_days(employee_id: int, days: tuple[date, ...]) -> list[DayResult]:
    return [result(Outcome.OK, employee_id=employee_id, day=d) for d in days]


STREAK = [result(Outcome.ABSENT, employee_id=1, day=d) for d in (WED, THU, FRI)]
REST_CHECKIN = [
    replace(
        result(Outcome.UNREGISTERED_CHANGE, employee_id=2, day=TUE),
        checkin=datetime(2026, 9, 22, 16, 38),
    )
]
LATES = [result(Outcome.LATE, employee_id=1, day=d) for d in (MON, TUE)]
LATE_HISTORY = [result(Outcome.LATE, employee_id=1, day=date(2026, 9, d)) for d in (9, 16)]
ABSENCE_WITH_NOTE = [
    result(Outcome.ABSENT, employee_id=2, day=MON, comment="Avisó BETO PRUEBA por teléfono")
]
NO_RULE = [AttendanceWarning(WarningCode.NO_REST_RULE, 2, MON, "Sin regla de descanso vigente")]

SCENARIOS = (
    Scenario("semana limpia", make_context(_ok_days(1, (MON, WED)) + _ok_days(2, (MON, WED)))),
    Scenario(
        "racha sin checar",
        make_context(STREAK + _ok_days(2, (WED, THU))),
        expected_high=frozenset({FindingKind.NO_CHECKIN_STREAK}),
        expected_actions={FindingKind.NO_CHECKIN_STREAK: JUSTIFY_OR_EXCEPTION},
    ),
    Scenario(
        "checada en descanso",
        make_context(REST_CHECKIN),
        expected_actions={FindingKind.REST_DAY_CHECKIN: frozenset({SuggestedAction.REST_SWAP})},
    ),
    Scenario(
        "retardos repetidos",
        make_context(LATES, history=LATE_HISTORY),
        expected_actions={
            FindingKind.REPEATED_LATE: frozenset({SuggestedAction.NONE, SuggestedAction.JUSTIFY})
        },
    ),
    Scenario(
        "aviso de configuración",
        make_context(warnings=NO_RULE),
        expected_actions={FindingKind.CONFIG_WARNING: frozenset({SuggestedAction.FIX_CONFIG})},
    ),
    Scenario(
        "falta con comentario",
        make_context(ABSENCE_WITH_NOTE),
        expected_high=frozenset({FindingKind.ABSENT_NO_EXCEPTION}),
        expected_actions={FindingKind.ABSENT_NO_EXCEPTION: JUSTIFY_OR_EXCEPTION},
    ),
    Scenario(
        "semana mezclada",
        make_context(STREAK + REST_CHECKIN + ABSENCE_WITH_NOTE, warnings=NO_RULE),
        expected_high=frozenset({FindingKind.NO_CHECKIN_STREAK, FindingKind.ABSENT_NO_EXCEPTION}),
        expected_actions={
            FindingKind.REST_DAY_CHECKIN: frozenset({SuggestedAction.REST_SWAP}),
            FindingKind.CONFIG_WARNING: frozenset({SuggestedAction.FIX_CONFIG}),
        },
    ),
)
