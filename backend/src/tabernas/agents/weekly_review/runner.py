"""LiveReviewAgent: an append-only tool loop over the Messages API (spec §5.1, §5.4)."""

from collections.abc import Sequence
from typing import Any

from tabernas.agents.weekly_review.agent import AgentApiError, AgentOutcome, MessagesApi, ToolCall
from tabernas.agents.weekly_review.prompt import SYSTEM_PROMPT, opening_message, retry_message
from tabernas.agents.weekly_review.schema import (
    NARRATIVE_SCHEMA,
    NarrativeFormatError,
    parse_narrative,
)
from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS, ReviewTools, ToolError
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.domain.review_types import Narrative, ReviewContext

MAX_TURNS = 8
MAX_RETRIES = 1
MAX_TOKENS = 16000
EFFORT = "medium"
STOP_MESSAGES = {
    "refusal": "Claude declinó redactar este borrador.",
    "max_tokens": "La respuesta del agente se cortó por longitud.",
}
TURN_LIMIT_MESSAGE = f"El agente excedió el límite de {MAX_TURNS} vueltas."
Tokens = tuple[int, int]


class LiveReviewAgent:
    def __init__(self, api: MessagesApi, model: str) -> None:
        self._api = api
        self._model = model

    def run(self, context: ReviewContext) -> AgentOutcome:
        tools = ReviewTools(context)
        messages: list[dict[str, Any]] = [{"role": "user", "content": opening_message(context)}]
        tokens: Tokens = (0, 0)
        attempts = 0
        try:
            for _ in range(MAX_TURNS):
                turn = self._api.send(self._params(messages))
                tokens = (tokens[0] + turn.input_tokens, tokens[1] + turn.output_tokens)
                messages.append({"role": "assistant", "content": list(turn.content)})
                if turn.stop_reason == "tool_use":
                    results = tool_results(tools, turn.tool_calls)
                    messages.append({"role": "user", "content": results})
                    continue
                if turn.stop_reason != "end_turn":
                    return self._outcome(None, stop_message(turn.stop_reason), tokens, attempts)
                attempts += 1
                narrative, errors = check_answer(turn.text, context)
                if not errors:
                    return self._outcome(narrative, None, tokens, attempts)
                if attempts > MAX_RETRIES:
                    failure = "Validación fallida: " + "; ".join(errors)
                    return self._outcome(None, failure, tokens, attempts)
                messages.append({"role": "user", "content": retry_message(errors)})
        except AgentApiError as exc:
            return self._outcome(None, str(exc), tokens, attempts)
        return self._outcome(None, TURN_LIMIT_MESSAGE, tokens, attempts)

    def _params(self, messages: Sequence[dict[str, Any]]) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_tokens": MAX_TOKENS,
            "system": [
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            "tools": TOOL_DEFINITIONS,
            "output_config": {
                "effort": EFFORT,
                "format": {"type": "json_schema", "schema": NARRATIVE_SCHEMA},
            },
            "messages": list(messages),
        }

    def _outcome(
        self, narrative: Narrative | None, error: str | None, tokens: Tokens, attempts: int
    ) -> AgentOutcome:
        return AgentOutcome(
            narrative=narrative,
            error=error,
            model=self._model,
            input_tokens=tokens[0],
            output_tokens=tokens[1],
            attempts=attempts,
        )


def stop_message(stop_reason: str) -> str:
    return STOP_MESSAGES.get(stop_reason, f"El agente se detuvo inesperadamente ({stop_reason}).")


def tool_results(tools: ReviewTools, calls: Sequence[ToolCall]) -> list[dict[str, Any]]:
    return [_tool_result(tools, call) for call in calls]


def _tool_result(tools: ReviewTools, call: ToolCall) -> dict[str, Any]:
    try:
        content = tools.call(call.name, call.input)
    except ToolError as exc:
        block = {"type": "tool_result", "tool_use_id": call.id, "content": str(exc)}
        return {**block, "is_error": True}
    return {"type": "tool_result", "tool_use_id": call.id, "content": content}


def check_answer(text: str, context: ReviewContext) -> tuple[Narrative | None, list[str]]:
    try:
        narrative = parse_narrative(text)
    except NarrativeFormatError as exc:
        return None, [str(exc)]
    return narrative, validate_narrative(narrative, context.findings, context.employees)
