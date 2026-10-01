"""Picks the weekly-review agent from settings (spec E8)."""

import anthropic

from tabernas.agents.weekly_review.agent import AgentOutcome, ReviewAgent
from tabernas.agents.weekly_review.anthropic_api import AnthropicMessages
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.config import Settings
from tabernas.domain.review_types import ReviewContext

API_TIMEOUT_SECONDS = 120.0
API_MAX_RETRIES = 2
MISSING_KEY_MESSAGE = "Falta ANTHROPIC_API_KEY: el borrador se guardó sin narrativa."


class UnconfiguredReviewAgent:
    """REVIEW_AGENT=live without a key: drafts keep findings and RH rows, no narrative."""

    def run(self, context: ReviewContext) -> AgentOutcome:
        return AgentOutcome(narrative=None, error=MISSING_KEY_MESSAGE, model=None)


def build_review_agent(settings: Settings) -> ReviewAgent:
    if settings.review_agent == "fake":
        return FakeReviewAgent()
    key = settings.anthropic_api_key.get_secret_value()
    if not key:
        return UnconfiguredReviewAgent()
    client = anthropic.Anthropic(
        api_key=key, timeout=API_TIMEOUT_SECONDS, max_retries=API_MAX_RETRIES
    )
    return LiveReviewAgent(AnthropicMessages(client), settings.review_model)
