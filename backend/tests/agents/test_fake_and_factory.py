from dataclasses import replace
from datetime import date, datetime

from tabernas.agents.weekly_review.factory import (
    MISSING_KEY_MESSAGE,
    UnconfiguredReviewAgent,
    build_review_agent,
)
from tabernas.agents.weekly_review.fake import FAKE_MODEL, FakeReviewAgent
from tabernas.agents.weekly_review.runner import LiveReviewAgent
from tabernas.agents.weekly_review.validate import validate_narrative
from tabernas.config import Settings
from tabernas.domain.review_types import FindingKind, ReviewContext, SuggestedAction
from tabernas.domain.types import AttendanceWarning, Outcome, WarningCode
from tests.agents.helpers import make_context
from tests.domain.factories import result

MON, TUE, WED, THU = (date(2026, 9, d) for d in (21, 22, 23, 24))


def every_kind() -> ReviewContext:
    week = [
        replace(
            result(Outcome.UNREGISTERED_CHANGE, employee_id=1, day=TUE),
            checkin=datetime(2026, 9, 22, 16, 41),
        ),
        result(Outcome.ABSENT, employee_id=2, day=MON),
        result(Outcome.ABSENT, employee_id=1, day=WED),
        result(Outcome.ABSENT, employee_id=1, day=THU),
        result(Outcome.LATE, employee_id=2, day=WED),
        result(Outcome.LATE, employee_id=2, day=THU),
    ]
    warnings = [AttendanceWarning(WarningCode.MISSING_RH_NAME, 2, None, "sin nombre RH")]
    return make_context(week, warnings=warnings)


def test_fake_agent_output_passes_the_validator() -> None:
    context = every_kind()
    assert {f.kind for f in context.findings} == set(FindingKind)
    outcome = FakeReviewAgent().run(context)
    assert outcome.narrative is not None and outcome.model == FAKE_MODEL
    assert validate_narrative(outcome.narrative, context.findings, context.employees) == []
    actions = {
        next(f.kind for f in context.findings if f.id == item.finding_id): item.suggested_action
        for item in outcome.narrative.items
    }
    assert actions[FindingKind.REST_DAY_CHECKIN] == SuggestedAction.REST_SWAP
    assert actions[FindingKind.CONFIG_WARNING] == SuggestedAction.FIX_CONFIG


def test_fake_agent_on_an_empty_week() -> None:
    outcome = FakeReviewAgent().run(make_context())
    assert outcome.narrative is not None
    assert outcome.narrative.items == ()
    assert "sin pendientes" in outcome.narrative.summary


def test_factory_returns_the_fake_agent_in_fake_mode() -> None:
    settings = Settings(_env_file=None, review_agent="fake")  # type: ignore[call-arg]
    assert isinstance(build_review_agent(settings), FakeReviewAgent)


def test_live_mode_without_key_saves_drafts_without_narrative() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        review_agent="live",
        anthropic_api_key="",  # type: ignore[arg-type]
    )
    agent = build_review_agent(settings)
    assert isinstance(agent, UnconfiguredReviewAgent)
    outcome = agent.run(make_context())
    assert (outcome.narrative, outcome.error) == (None, MISSING_KEY_MESSAGE)


def test_live_mode_with_key_builds_the_real_agent() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        review_agent="live",
        anthropic_api_key="sk-test",  # type: ignore[arg-type]
    )
    assert isinstance(build_review_agent(settings), LiveReviewAgent)
