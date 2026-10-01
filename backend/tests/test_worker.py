from collections.abc import Callable
from datetime import datetime, timedelta

from sqlalchemy import func, update
from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.review_types import ReviewContext, ReviewStatus, ReviewTrigger
from tabernas.repos.reviews import STALE_RUNNING_MESSAGE, ReviewRepo
from tabernas.worker import INTERNAL_ERROR_MESSAGE, fail_stale, run_next, schedule_due, tick
from tests.support import StubSource

Factory = sessionmaker[Session]
THURSDAY_EVENING = datetime(2026, 9, 24, 17, 31)
SATURDAY_NOON = datetime(2026, 9, 26, 12, 0)


def at(moment: datetime) -> Callable[[], datetime]:
    return lambda: moment


class ExplodingAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        raise RuntimeError("boom")


def statuses(factory: Factory) -> list[ReviewStatus]:
    with factory() as session:
        return [review.status for review in ReviewRepo(session).find_all()]


def test_schedule_due_enqueues_the_thursday_slot_once(session_factory: Factory) -> None:
    review = schedule_due(session_factory, at(THURSDAY_EVENING))
    assert review is not None
    assert (review.trigger, review.iso_year, review.iso_week) == (
        ReviewTrigger.THURSDAY,
        2026,
        39,
    )
    assert schedule_due(session_factory, at(THURSDAY_EVENING)) is None
    assert statuses(session_factory) == [ReviewStatus.QUEUED]


def test_schedule_due_skips_slots_older_than_a_day(session_factory: Factory) -> None:
    assert schedule_due(session_factory, at(SATURDAY_NOON)) is None
    assert statuses(session_factory) == []


def test_schedule_due_waits_for_a_manual_run_of_the_same_week(session_factory: Factory) -> None:
    with session_factory() as session:
        ReviewRepo(session).enqueue(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL)
        session.commit()
    assert schedule_due(session_factory, at(THURSDAY_EVENING)) is None
    assert statuses(session_factory) == [ReviewStatus.QUEUED]


def test_run_next_processes_the_queue(session_factory: Factory) -> None:
    schedule_due(session_factory, at(THURSDAY_EVENING))
    clock = at(THURSDAY_EVENING)
    done = run_next(session_factory, StubSource(), clock, FakeReviewAgent())
    assert done is not None and done.status == ReviewStatus.READY
    assert run_next(session_factory, StubSource(), clock, FakeReviewAgent()) is None


def test_unexpected_errors_fail_the_review(session_factory: Factory) -> None:
    schedule_due(session_factory, at(THURSDAY_EVENING))
    failed = run_next(session_factory, StubSource(), at(THURSDAY_EVENING), ExplodingAgent())
    assert failed is not None
    assert (failed.status, failed.error) == (ReviewStatus.FAILED, INTERNAL_ERROR_MESSAGE)


def test_fail_stale_frees_interrupted_runs(session_factory: Factory) -> None:
    # Review Focus #4
    schedule_due(session_factory, at(THURSDAY_EVENING))
    with session_factory() as session:
        ReviewRepo(session).claim_next()
        session.execute(
            update(WeeklyReviewRow).values(updated_at=func.now() - timedelta(minutes=20))
        )
        session.commit()
    assert fail_stale(session_factory) == 1
    with session_factory() as session:
        (review,) = ReviewRepo(session).find_all()
    assert (review.status, review.error) == (ReviewStatus.FAILED, STALE_RUNNING_MESSAGE)


def test_tick_schedules_and_runs(session_factory: Factory) -> None:
    tick(session_factory, StubSource(), at(THURSDAY_EVENING), FakeReviewAgent())
    assert statuses(session_factory) == [ReviewStatus.READY]
