"""Adapter from the anthropic SDK to MessagesApi: SDK types and errors stop here."""

from collections.abc import Mapping
from typing import Any

import anthropic

from tabernas.agents.weekly_review.agent import AgentApiError, ModelTurn, ToolCall

# Server-side fallback on refusals: Anthropic picks the fallback model by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicMessages:
    def __init__(self, client: anthropic.Anthropic) -> None:
        self._client = client

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        try:
            message = self._client.beta.messages.create(
                **params, betas=[FALLBACK_BETA], fallbacks="default"
            )
        except anthropic.RateLimitError as exc:
            raise AgentApiError(
                "La API de Claude está limitando las solicitudes; intenta más tarde."
            ) from exc
        except anthropic.APIStatusError as exc:
            status = exc.status_code
            raise AgentApiError(f"La API de Claude respondió con error {status}.") from exc
        except anthropic.APIConnectionError as exc:
            raise AgentApiError("No se pudo conectar con la API de Claude.") from exc
        except anthropic.APIError as exc:
            raise AgentApiError("Error inesperado de la API de Claude.") from exc
        return to_model_turn(message)


def _final_text(content: tuple[Any, ...]) -> str:
    """Text after the last fallback block: the declining model's partial text is dropped."""
    start = 0
    for index, block in enumerate(content):
        if block.type == "fallback":
            start = index + 1
    return "".join(block.text for block in content[start:] if block.type == "text")


def to_model_turn(message: Any) -> ModelTurn:
    content = tuple(message.content)
    usage = message.usage
    cached = (getattr(usage, "cache_read_input_tokens", None) or 0) + (
        getattr(usage, "cache_creation_input_tokens", None) or 0
    )
    return ModelTurn(
        stop_reason=message.stop_reason or "",
        content=content,
        text=_final_text(content),
        tool_calls=tuple(
            ToolCall(id=block.id, name=block.name, input=dict(block.input))
            for block in content
            if block.type == "tool_use"
        ),
        input_tokens=usage.input_tokens + cached,
        output_tokens=usage.output_tokens,
    )
