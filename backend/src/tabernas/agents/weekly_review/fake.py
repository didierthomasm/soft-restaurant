"""Deterministic agent for REVIEW_AGENT=fake (demo, E2E, CI): no API calls, same contract."""

from collections.abc import Sequence

from tabernas.agents.pseudonyms import alias
from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ReviewContext,
    SuggestedAction,
)

FAKE_MODEL = "fake"
PRIORITY_BY_KIND = {
    FindingKind.REST_DAY_CHECKIN: Priority.MEDIUM,
    FindingKind.ABSENT_NO_EXCEPTION: Priority.HIGH,
    FindingKind.NO_CHECKIN_STREAK: Priority.HIGH,
    FindingKind.REPEATED_LATE: Priority.MEDIUM,
    FindingKind.CONFIG_WARNING: Priority.LOW,
}
ACTION_BY_KIND = {
    FindingKind.REST_DAY_CHECKIN: SuggestedAction.REST_SWAP,
    FindingKind.ABSENT_NO_EXCEPTION: SuggestedAction.JUSTIFY,
    FindingKind.NO_CHECKIN_STREAK: SuggestedAction.ADD_EXCEPTION,
    FindingKind.REPEATED_LATE: SuggestedAction.NONE,
    FindingKind.CONFIG_WARNING: SuggestedAction.FIX_CONFIG,
}
TEMPLATES = {
    FindingKind.REST_DAY_CHECKIN: "{who} checó en su día de descanso; probablemente fue un "
    "cambio de descanso sin registrar.",
    FindingKind.ABSENT_NO_EXCEPTION: "{who} faltó sin justificación ni excepción registrada.",
    FindingKind.NO_CHECKIN_STREAK: "{who} lleva varios días laborales seguidos sin checar.",
    FindingKind.REPEATED_LATE: "{who} acumula retardos repetidos.",
    FindingKind.CONFIG_WARNING: "Hay un aviso de configuración que conviene corregir.",
}


class FakeReviewAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        items = tuple(_item(finding) for finding in context.findings)
        narrative = Narrative(summary=_summary(context, items), items=items)
        return AgentOutcome(narrative=narrative, error=None, model=FAKE_MODEL, attempts=1)


def _who(finding: Finding) -> str:
    if finding.employee_id is None:
        return "Un empleado"
    return "{" + alias(finding.employee_id) + "}"


def _item(finding: Finding) -> NarrativeItem:
    return NarrativeItem(
        finding_id=finding.id,
        priority=PRIORITY_BY_KIND[finding.kind],
        explanation=TEMPLATES[finding.kind].format(who=_who(finding)),
        suggested_action=ACTION_BY_KIND[finding.kind],
    )


def _summary(context: ReviewContext, items: Sequence[NarrativeItem]) -> str:
    week = f"{context.iso_year}-W{context.iso_week:02d}"
    if not items:
        return f"Semana {week}: sin pendientes. Borrador de demostración."
    high = sum(item.priority == Priority.HIGH for item in items)
    return (
        f"Semana {week}: {len(items)} hallazgos, {high} de prioridad alta. "
        "Borrador de demostración."
    )
