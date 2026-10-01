"""Contracts of the weekly-review agent: what the loop needs from the Messages API and
what any agent (live, fake, unconfigured) returns to the service."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from tabernas.domain.review_types import Narrative, ReviewContext


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    input: Mapping[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    """One Messages API response, reduced to what the loop reads.

    `content` holds the raw blocks and is sent back unchanged (append-only history)."""

    stop_reason: str
    content: tuple[Any, ...]
    text: str
    tool_calls: tuple[ToolCall, ...]
    input_tokens: int
    output_tokens: int


class AgentApiError(RuntimeError):
    """The Messages API failed after the SDK's retries. The message is safe to store."""


class MessagesApi(Protocol):
    def send(self, params: Mapping[str, Any]) -> ModelTurn: ...


@dataclass(frozen=True)
class AgentOutcome:
    narrative: Narrative | None
    error: str | None
    model: str | None
    input_tokens: int = 0
    output_tokens: int = 0
    attempts: int = 0


class ReviewAgent(Protocol):
    def run(self, context: ReviewContext) -> AgentOutcome: ...
