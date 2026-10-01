"""Structured final answer of the weekly-review agent (spec §5.3)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from tabernas.domain.review_types import Narrative, NarrativeItem, Priority, SuggestedAction

_ITEM_FIELDS = ["finding_id", "priority", "explanation", "suggested_action"]

NARRATIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "finding_id": {"type": "string"},
                    "priority": {"type": "string", "enum": [p.value for p in Priority]},
                    "explanation": {"type": "string"},
                    "suggested_action": {
                        "type": "string",
                        "enum": [a.value for a in SuggestedAction],
                    },
                },
                "required": _ITEM_FIELDS,
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "items"],
    "additionalProperties": False,
}


class NarrativeFormatError(ValueError):
    """The final answer is not JSON matching NARRATIVE_SCHEMA."""


class _ItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


class _NarrativeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str
    items: list[_ItemModel]


def parse_narrative(text: str) -> Narrative:
    try:
        parsed = _NarrativeModel.model_validate_json(text)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or 'raíz'}: {error['msg']}"
            for error in exc.errors()[:3]
        )
        raise NarrativeFormatError(f"La respuesta no cumple el esquema ({details})") from exc
    return Narrative(
        summary=parsed.summary.strip(),
        items=tuple(
            NarrativeItem(
                finding_id=item.finding_id,
                priority=item.priority,
                explanation=item.explanation.strip(),
                suggested_action=item.suggested_action,
            )
            for item in parsed.items
        ),
    )
