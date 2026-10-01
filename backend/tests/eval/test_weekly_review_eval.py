"""Live evaluation of the weekly-review agent (spec §10.2). Costs money: local only.

Run from backend/: uv run pytest -m agent -s   (needs ANTHROPIC_API_KEY in .env)"""

import json
from collections.abc import Mapping
from typing import Any

import anthropic
import pytest

from tabernas.agents.weekly_review.agent import ModelTurn
from tabernas.agents.weekly_review.anthropic_api import AnthropicMessages
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.config import Settings
from tabernas.domain.review_types import Priority
from tests.eval.scenarios import SCENARIOS, Scenario

pytestmark = pytest.mark.agent

INPUT_USD_PER_MTOK = 4.0  # claude-opus-5-5 list price; cache reads are cheaper
OUTPUT_USD_PER_MTOK = 20.0


class RecordingMessages:
    """Wraps the real adapter and keeps every payload sent, to check for names."""

    def __init__(self, inner: AnthropicMessages) -> None:
        self._inner = inner
        self.payloads: list[str] = []

    def send(self, params: Mapping[str, Any]) -> ModelTurn:
        self.payloads.append(json.dumps(params, ensure_ascii=False, default=str))
        return self._inner.send(params)


@pytest.fixture(scope="module")
def live() -> tuple[anthropic.Anthropic, str]:
    settings = Settings()
    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        pytest.skip("ANTHROPIC_API_KEY no está configurada")
    return anthropic.Anthropic(api_key=key, timeout=120.0, max_retries=2), settings.review_model


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda s: s.name)
def test_agent_on_synthetic_week(scenario: Scenario, live: tuple[anthropic.Anthropic, str]) -> None:
    client, model = live
    api = RecordingMessages(AnthropicMessages(client))
    outcome = LiveReviewAgent(api, model).run(scenario.context)
    cost = (
        outcome.input_tokens * INPUT_USD_PER_MTOK + outcome.output_tokens * OUTPUT_USD_PER_MTOK
    ) / 1_000_000
    print(
        f"\n[{scenario.name}] intentos={outcome.attempts} llamadas={len(api.payloads)} "
        f"tokens={outcome.input_tokens}/{outcome.output_tokens} costo≈${cost:.4f}"
    )
    sent = "\n".join(api.payloads).casefold()
    for employee in scenario.context.employees:
        for name in filter(None, (employee.short_name, employee.rh_name)):
            assert name.casefold() not in sent, f"{name} salió hacia la API"
    assert outcome.narrative is not None, outcome.error
    assert outcome.attempts == 1, "el validador debe pasar a la primera"
    kinds = {finding.id: finding.kind for finding in scenario.context.findings}
    for item in outcome.narrative.items:
        kind = kinds[item.finding_id]
        if kind in scenario.expected_high:
            assert item.priority == Priority.HIGH, item
        allowed = scenario.expected_actions.get(kind)
        if allowed:
            assert item.suggested_action in allowed, item
