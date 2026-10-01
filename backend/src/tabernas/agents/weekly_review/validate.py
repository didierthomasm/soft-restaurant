"""Checks the agent's answer against the deterministic findings (spec §5.4).

The guarantee "never omits, never invents" lives here, not in the prompt."""

from collections import Counter
from collections.abc import Sequence

from tabernas.agents.pseudonyms import alias, aliases_in, contains_known_name
from tabernas.domain.review_types import Finding, Narrative
from tabernas.domain.types import Employee

NAME_ERROR = (
    "El texto usa nombres reales; nombra a los empleados solo con su seudónimo, p. ej. {E12}."
)


def validate_narrative(
    narrative: Narrative, findings: Sequence[Finding], employees: Sequence[Employee]
) -> list[str]:
    return [*_coverage_errors(narrative, findings), *_text_errors(narrative, employees)]


def _coverage_errors(narrative: Narrative, findings: Sequence[Finding]) -> list[str]:
    expected = [finding.id for finding in findings]
    counts = Counter(item.finding_id for item in narrative.items)
    missing = [finding_id for finding_id in expected if finding_id not in counts]
    repeated = sorted(finding_id for finding_id, count in counts.items() if count > 1)
    unknown = sorted(set(counts) - set(expected))
    checks = (
        ("Faltan hallazgos", missing),
        ("Hallazgos repetidos", repeated),
        ("Hallazgos que no existen", unknown),
    )
    return [f"{label}: {', '.join(ids)}" for label, ids in checks if ids]


def _text_errors(narrative: Narrative, employees: Sequence[Employee]) -> list[str]:
    texts = [narrative.summary, *(item.explanation for item in narrative.items)]
    valid = {alias(employee.id) for employee in employees}
    unknown = sorted({found for text in texts for found in aliases_in(text)} - valid)
    errors: list[str] = []
    if not narrative.summary.strip():
        errors.append("El resumen está vacío.")
    if unknown:
        errors.append("Seudónimos desconocidos: " + ", ".join(f"{{{a}}}" for a in unknown))
    if any(contains_known_name(text, employees) for text in texts):
        errors.append(NAME_ERROR)
    return errors
