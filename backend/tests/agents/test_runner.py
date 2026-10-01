import copy
import json
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

import pytest

from tabernas.agents.weekly_review.agent import AgentApiError, ModelTurn, ToolCall
from tabernas.agents.weekly_review.prompt import SYSTEM_PROMPT
from tabernas.agents.weekly_review.runner import MAX_TURNS, LiveReviewAgent
from tabernas.agents.weekly_review.schema import NARRATIVE_SCHEMA
from tabernas.agents.weekly_review.tools import TOOL_DEFINITIONS
from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import Outcome
from tests.agents.helpers import make_context
from tests.domain.factories import result

MODEL = "claude-opus-5-5"
FINDINGS_CALL = ToolCall("tu_1", "get_week_findings", {})


class ScriptedApi:
    """MessagesApi double: replays turns (or raises them) and records every request."""

    def __init__(self, turns: Sequence[ModelTurn | Exception]) -> None:
        self._turns = list(turns)
        self.requests: list[dict[str, Any]] = []

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        self.requests.append(copy.deepcopy(dict(params)))
        turn = self._turns.pop(0)
        if isinstance(turn, Exception):
            raise turn
        return turn


def tool_turn(*calls: ToolCall) -> ModelTurn:
    content = tuple(
        {"type": "tool_use", "id": c.id, "name": c.name, "input": dict(c.input)} for c in calls
    )
    return ModelTurn("tool_use", content, "", calls, input_tokens=100, output_tokens=10)


def final_turn(payload: Mapping[str, Any] | str, stop_reason: str = "end_turn") -> ModelTurn:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    content = ({"type": "text", "text": text},)
    return ModelTurn(stop_reason, content, text, (), input_tokens=200, output_tokens=50)


def answer(context: ReviewContext, skip: int = 0) -> dict[str, Any]:
    return {
        "summary": "Hay pendientes esta semana.",
        "items": [
            {
                "finding_id": f.id,
                "priority": "HIGH",
                "explanation": "Revisar el caso.",
                "suggested_action": "JUSTIFY",
            }
            for f in context.findings[skip:]
        ],
    }


def busy_context() -> ReviewContext:
    return make_context(
        [
            result(
                Outcome.ABSENT, employee_id=1, day=date(2026, 9, 23), comment="Avisó ANA PRUEBA"
            ),
            result(Outcome.ABSENT, employee_id=2, day=date(2026, 9, 21)),
        ]
    )


def run(api: ScriptedApi, context: ReviewContext | None = None) -> Any:
    return LiveReviewAgent(api, MODEL).run(context or busy_context())


def test_system_prompt_documents_every_kind_and_action() -> None:
    for value in [*(k.value for k in FindingKind), *(a.value for a in SuggestedAction)]:
        assert value in SYSTEM_PROMPT


def test_happy_path_reads_findings_and_returns_a_valid_narrative() -> None:
    context = busy_context()
    api = ScriptedApi([tool_turn(FINDINGS_CALL), final_turn(answer(context))])
    outcome = run(api, context)
    assert outcome.error is None and outcome.narrative is not None
    assert [i.finding_id for i in outcome.narrative.items] == [f.id for f in context.findings]
    assert (outcome.model, outcome.attempts) == (MODEL, 1)
    assert (outcome.input_tokens, outcome.output_tokens) == (300, 60)
    tool_message = api.requests[1]["messages"][-1]
    assert tool_message["role"] == "user"
    assert tool_message["content"][0]["tool_use_id"] == "tu_1"
    assert json.loads(tool_message["content"][0]["content"])[0]["id"] == context.findings[0].id


def test_request_shape() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn(answer(context))])
    run(api, context)
    request = api.requests[0]
    assert (request["model"], request["max_tokens"]) == (MODEL, 16000)
    assert request["output_config"] == {
        "effort": "medium",
        "format": {"type": "json_schema", "schema": NARRATIVE_SCHEMA},
    }
    assert request["system"] == [
        {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
    ]
    assert request["tools"] == TOOL_DEFINITIONS
    assert request["messages"][0]["role"] == "user"
    assert "2026-W39" in request["messages"][0]["content"]


def test_history_is_append_only() -> None:
    context = busy_context()
    api = ScriptedApi([tool_turn(FINDINGS_CALL), final_turn(answer(context))])
    run(api, context)
    first, second = api.requests[0]["messages"], api.requests[1]["messages"]
    assert second[: len(first)] == first


def test_missing_finding_triggers_one_retry() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn(answer(context, skip=1)), final_turn(answer(context))])
    outcome = run(api, context)
    assert outcome.narrative is not None and outcome.attempts == 2
    retry = api.requests[1]["messages"][-1]
    assert retry["role"] == "user" and "Faltan hallazgos" in retry["content"]


def test_two_invalid_answers_give_no_narrative() -> None:
    context = busy_context()
    api = ScriptedApi([final_turn("no es json"), final_turn(answer(context, skip=1))])
    outcome = run(api, context)
    assert outcome.narrative is None and outcome.attempts == 2
    assert outcome.error is not None and outcome.error.startswith("Validación fallida: ")


def test_tool_errors_go_back_as_is_error_results() -> None:
    context = busy_context()
    bad = ToolCall("tu_9", "get_employee_week", {"employee": "E99"})
    api = ScriptedApi([tool_turn(bad), final_turn(answer(context))])
    assert run(api, context).narrative is not None
    block = api.requests[1]["messages"][-1]["content"][0]
    assert block["is_error"] is True and "E99" in block["content"]


@pytest.mark.parametrize(
    ("stop_reason", "message"),
    [("refusal", "declinó"), ("max_tokens", "se cortó")],
)
def test_other_stop_reasons_give_no_narrative(stop_reason: str, message: str) -> None:
    outcome = run(ScriptedApi([final_turn("{}", stop_reason=stop_reason)]))
    assert outcome.narrative is None and message in (outcome.error or "")


def test_pause_turn_resumes_and_gives_a_narrative() -> None:
    context = busy_context()
    paused = ModelTurn("pause_turn", ({"type": "text", "text": "..."},), "", (), 10, 1)
    api = ScriptedApi([paused, final_turn(answer(context))])
    outcome = run(api, context)
    assert outcome.narrative is not None and outcome.attempts == 1
    assert api.requests[1]["messages"][-1]["role"] == "assistant"


def test_turn_limit() -> None:
    api = ScriptedApi([tool_turn(FINDINGS_CALL)] * MAX_TURNS)
    outcome = run(api)
    assert outcome.narrative is None and "límite" in (outcome.error or "")
    assert len(api.requests) == MAX_TURNS


def test_api_errors_are_reported() -> None:
    outcome = run(ScriptedApi([AgentApiError("No se pudo conectar con la API de Claude.")]))
    assert outcome.narrative is None
    assert outcome.error == "No se pudo conectar con la API de Claude."


def test_empty_week_is_a_valid_narrative() -> None:
    api = ScriptedApi([final_turn({"summary": "Semana sin pendientes.", "items": []})])
    assert run(api, make_context()).narrative is not None


def test_no_employee_name_is_ever_sent() -> None:
    # Review Focus #1: names must not reach the API, not even through tool results.
    context = busy_context()
    calls = [
        FINDINGS_CALL,
        ToolCall("tu_2", "get_week_incidents", {}),
        ToolCall("tu_3", "get_employee_week", {"employee": "E1"}),
        ToolCall("tu_4", "get_employee_history", {"employee": "E1", "weeks": 8}),
    ]
    api = ScriptedApi([tool_turn(*calls), final_turn(answer(context))])
    run(api, context)
    sent = json.dumps(api.requests, ensure_ascii=False).casefold()
    for employee in context.employees:
        for name in (employee.short_name, employee.rh_name or employee.short_name):
            assert name.casefold() not in sent
