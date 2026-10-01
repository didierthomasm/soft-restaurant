"""JSON shape of a review snapshot (jsonb columns). Keep keys stable: old rows must load."""

from datetime import date
from typing import Any

from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    SuggestedAction,
)
from tabernas.domain.types import RhType

Json = dict[str, Any]


def finding_to_json(finding: Finding) -> Json:
    return {
        "id": finding.id,
        "kind": finding.kind.value,
        "employee_id": finding.employee_id,
        "days": [day.isoformat() for day in finding.days],
        "facts": [[key, value] for key, value in finding.facts],
    }


def finding_from_json(data: Json) -> Finding:
    return Finding(
        id=str(data["id"]),
        kind=FindingKind(data["kind"]),
        employee_id=data["employee_id"],
        days=tuple(date.fromisoformat(day) for day in data["days"]),
        facts=tuple((str(key), value) for key, value in data["facts"]),
    )


def rh_row_to_json(row: ProposedRhRow) -> Json:
    return {
        "employee_id": row.employee_id,
        "day": row.day.isoformat(),
        "rh_type": row.rh_type.value,
        "comment": row.comment,
    }


def rh_row_from_json(data: Json) -> ProposedRhRow:
    return ProposedRhRow(
        employee_id=int(data["employee_id"]),
        day=date.fromisoformat(data["day"]),
        rh_type=RhType(data["rh_type"]),
        comment=str(data["comment"]),
    )


def narrative_to_json(narrative: Narrative) -> Json:
    return {
        "summary": narrative.summary,
        "items": [
            {
                "finding_id": item.finding_id,
                "priority": item.priority.value,
                "explanation": item.explanation,
                "suggested_action": item.suggested_action.value,
            }
            for item in narrative.items
        ],
    }


def narrative_from_json(data: Json) -> Narrative:
    return Narrative(
        summary=str(data["summary"]),
        items=tuple(
            NarrativeItem(
                finding_id=str(item["finding_id"]),
                priority=Priority(item["priority"]),
                explanation=str(item["explanation"]),
                suggested_action=SuggestedAction(item["suggested_action"]),
            )
            for item in data["items"]
        ),
    )
