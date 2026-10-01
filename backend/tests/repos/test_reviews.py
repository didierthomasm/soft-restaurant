from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import func, update
from sqlalchemy.orm import Session

from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.review_types import (
    Finding,
    FindingKind,
    Narrative,
    NarrativeItem,
    Priority,
    ProposedRhRow,
    ReviewResult,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
    WeeklyReview,
)
from tabernas.domain.types import RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.reviews import STALE_RUNNING_MESSAGE, ReviewRepo

AS_OF = datetime(2026, 9, 24, 17, 30)
FINDING = Finding(
    id="NO_CHECKIN_STREAK:1:2026-09-23",
    kind=FindingKind.NO_CHECKIN_STREAK,
    employee_id=1,
    days=(date(2026, 9, 23), date(2026, 9, 24)),
    facts=(("days", 2),),
)
NARRATIVE = Narrative(
    summary="Dos días sin checar de {E1}.",
    items=(
        NarrativeItem(
            FINDING.id, Priority.HIGH, "Revisar con {E1}.", SuggestedAction.ADD_EXCEPTION
        ),
    ),
)
ROW = ProposedRhRow(
    employee_id=1, day=date(2026, 9, 23), rh_type=RhType.FALTA_INJUSTIFICADA, comment=""
)


def make_result(
    status: ReviewStatus = ReviewStatus.READY,
    narrative: Narrative | None = NARRATIVE,
    error: str | None = None,
) -> ReviewResult:
    return ReviewResult(
        status=status,
        as_of=AS_OF,
        findings=(FINDING,),
        rh_rows=(ROW,),
        narrative=narrative,
        model="claude-opus-5-5",
        input_tokens=1200,
        output_tokens=300,
        error=error,
    )


def enqueue(
    repo: ReviewRepo, week: int = 39, trigger: ReviewTrigger = ReviewTrigger.MANUAL
) -> WeeklyReview:
    return repo.enqueue(iso_year=2026, iso_week=week, trigger=trigger)


def test_enqueue_creates_a_queued_review(session: Session) -> None:
    review = enqueue(ReviewRepo(session))
    assert (review.iso_year, review.iso_week, review.status) == (2026, 39, ReviewStatus.QUEUED)
    assert review.created_at is not None
    assert review.findings == ()
    assert review.narrative is None


def test_only_one_review_in_progress_per_week(session: Session) -> None:
    repo = ReviewRepo(session)
    enqueue(repo)
    with pytest.raises(ConflictError, match="Ya se está generando"):
        enqueue(repo, trigger=ReviewTrigger.THURSDAY)
    enqueue(repo, week=40)  # another week is fine


def test_a_finished_review_frees_the_week(session: Session) -> None:
    repo = ReviewRepo(session)
    first = enqueue(repo)
    repo.fail(first.id, "algo falló")
    assert enqueue(repo).id != first.id


def test_invalid_iso_week_is_rejected(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        ReviewRepo(session).enqueue(iso_year=2025, iso_week=53, trigger=ReviewTrigger.MANUAL)


def test_claim_next_takes_the_oldest_queued(session: Session) -> None:
    repo = ReviewRepo(session)
    older, newer = enqueue(repo, week=38), enqueue(repo, week=39)
    first = repo.claim_next()
    assert first is not None and first.id == older.id and first.status == ReviewStatus.RUNNING
    second = repo.claim_next()
    assert second is not None and second.id == newer.id
    assert repo.claim_next() is None


def test_complete_round_trips_the_snapshot(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    repo.complete(review.id, make_result())
    loaded = repo.find_by_id(review.id)
    assert loaded.status == ReviewStatus.READY
    assert loaded.as_of == AS_OF
    assert loaded.findings == (FINDING,)
    assert loaded.rh_rows == (ROW,)
    assert loaded.narrative == NARRATIVE
    assert (loaded.model, loaded.input_tokens, loaded.output_tokens) == (
        "claude-opus-5-5",
        1200,
        300,
    )


def test_complete_without_narrative_truncates_long_errors(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    done = repo.complete(
        review.id, make_result(ReviewStatus.READY_NO_NARRATIVE, narrative=None, error="x" * 1500)
    )
    assert done.narrative is None
    assert done.findings == (FINDING,)
    assert done.error == "x" * 1000


def test_exists_is_per_trigger(session: Session) -> None:
    repo = ReviewRepo(session)
    enqueue(repo, trigger=ReviewTrigger.THURSDAY)
    assert repo.exists(iso_year=2026, iso_week=39, trigger=ReviewTrigger.THURSDAY)
    assert not repo.exists(iso_year=2026, iso_week=39, trigger=ReviewTrigger.MONDAY)


def test_only_ready_reviews_can_be_approved_once(session: Session) -> None:
    repo = ReviewRepo(session)
    review = enqueue(repo)
    with pytest.raises(ConflictError):
        repo.approve(review.id, AS_OF)
    repo.complete(review.id, make_result())
    approved = repo.approve(review.id, datetime(2026, 9, 24, 18, 0))
    assert approved.status == ReviewStatus.APPROVED
    assert approved.approved_at == datetime(2026, 9, 24, 18, 0)
    with pytest.raises(ConflictError):
        repo.approve(review.id, AS_OF)


def test_stale_running_reviews_fail_and_free_the_week(session: Session) -> None:
    # Review Focus #4: a crashed worker must not block the week forever.
    repo = ReviewRepo(session)
    stale, fresh = enqueue(repo, week=38), enqueue(repo, week=39)
    repo.claim_next()
    repo.claim_next()
    session.execute(
        update(WeeklyReviewRow)
        .where(WeeklyReviewRow.id == stale.id)
        .values(updated_at=func.now() - timedelta(minutes=20))
    )
    assert repo.fail_stale_running() == 1
    failed = repo.find_by_id(stale.id)
    assert (failed.status, failed.error) == (ReviewStatus.FAILED, STALE_RUNNING_MESSAGE)
    assert repo.find_by_id(fresh.id).status == ReviewStatus.RUNNING
    enqueue(repo, week=38)


def test_find_all_filters_and_orders_newest_first(session: Session) -> None:
    repo = ReviewRepo(session)
    a, b = enqueue(repo, week=38), enqueue(repo, week=39)
    assert [r.id for r in repo.find_all()] == [b.id, a.id]
    assert [r.id for r in repo.find_all(iso_year=2026, iso_week=38)] == [a.id]


def test_missing_review_is_not_found(session: Session) -> None:
    with pytest.raises(NotFoundError):
        ReviewRepo(session).find_by_id(999)
