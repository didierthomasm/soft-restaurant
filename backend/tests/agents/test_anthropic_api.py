from types import SimpleNamespace
from typing import Any, cast

import anthropic
import httpx2
import pytest

from tabernas.agents.weekly_review.agent import AgentApiError, ToolCall
from tabernas.agents.weekly_review.anthropic_api import (
    FALLBACK_BETA,
    AnthropicMessages,
    to_model_turn,
)

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def message(stop_reason: str = "tool_use") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text="Reviso los hallazgos. "),
            SimpleNamespace(type="tool_use", id="tu_1", name="get_week_findings", input={}),
        ],
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            cache_read_input_tokens=100,
            cache_creation_input_tokens=None,
        ),
    )


class FakeMessages:
    def __init__(self, outcome: Any) -> None:
        self._outcome = outcome
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


def client_with(outcome: Any) -> tuple[anthropic.Anthropic, FakeMessages]:
    messages = FakeMessages(outcome)
    client = SimpleNamespace(beta=SimpleNamespace(messages=messages))
    return cast(anthropic.Anthropic, client), messages


def test_to_model_turn_reduces_the_sdk_message() -> None:
    turn = to_model_turn(message())
    assert turn.stop_reason == "tool_use"
    assert turn.text == "Reviso los hallazgos. "
    assert turn.tool_calls == (ToolCall("tu_1", "get_week_findings", {}),)
    assert (turn.input_tokens, turn.output_tokens) == (110, 5)
    assert len(turn.content) == 3  # thinking blocks are kept to be sent back unchanged


def test_send_adds_the_fallback_beta_and_passes_params_through() -> None:
    client, messages = client_with(message("end_turn"))
    AnthropicMessages(client).send({"model": "claude-opus-5-5", "max_tokens": 10, "messages": []})
    assert messages.calls == [
        {
            "model": "claude-opus-5-5",
            "max_tokens": 10,
            "messages": [],
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }
    ]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (
            anthropic.RateLimitError(
                "rate", response=httpx2.Response(429, request=REQUEST), body=None
            ),
            "limitando",
        ),
        (
            anthropic.InternalServerError(
                "boom", response=httpx2.Response(500, request=REQUEST), body=None
            ),
            "500",
        ),
        (anthropic.APIConnectionError(request=REQUEST), "conectar"),
        (
            anthropic.APIResponseValidationError(
                httpx2.Response(200, request=REQUEST), body=None, message="bad shape"
            ),
            "inesperado",
        ),
    ],
)
def test_sdk_errors_become_agent_api_errors(error: Exception, expected: str) -> None:
    client, _ = client_with(error)
    with pytest.raises(AgentApiError, match=expected):
        AnthropicMessages(client).send({})


def test_text_before_a_fallback_block_is_dropped() -> None:
    msg = message("end_turn")
    msg.content = [
        SimpleNamespace(type="text", text='{"parcial'),
        SimpleNamespace(type="fallback"),
        SimpleNamespace(type="text", text='{"summary": "ok"}'),
    ]
    assert to_model_turn(msg).text == '{"summary": "ok"}'
