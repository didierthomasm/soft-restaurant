"""Weekly review drafts. Returns immutable domain objects, never ORM rows."""

from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tabernas.db.models import WeeklyReviewRow
from tabernas.domain.periods import validate_iso_week
from tabernas.domain.review_types import ReviewResult, ReviewStatus, ReviewTrigger, WeeklyReview
from tabernas.repos.errors import ConflictError, NotFoundError
from tabernas.repos.review_codec import (
    finding_from_json,
    finding_to_json,
    narrative_from_json,
    narrative_to_json,
    rh_row_from_json,
    rh_row_to_json,
)

STALE_RUNNING_AFTER = timedelta(minutes=15)
STALE_RUNNING_MESSAGE = "La corrida se interrumpió; genera el borrador de nuevo."
APPROVABLE = frozenset({ReviewStatus.READY, ReviewStatus.READY_NO_NARRATIVE})
MAX_ERROR_LENGTH = 1000


def to_review(row: WeeklyReviewRow) -> WeeklyReview:
    return WeeklyReview(
        id=row.id,
        iso_year=row.iso_year,
        iso_week=row.iso_week,
        trigger=row.trigger,
        status=row.status,
        created_at=row.created_at,
        as_of=row.as_of,
        findings=tuple(finding_from_json(item) for item in row.findings or ()),
        rh_rows=tuple(rh_row_from_json(item) for item in row.rh_rows or ()),
        narrative=narrative_from_json(row.narrative) if row.narrative is not None else None,
        model=row.model,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        error=row.error,
        approved_at=row.approved_at,
    )


def _truncate(error: str | None) -> str | None:
    return None if error is None else error[:MAX_ERROR_LENGTH]


class ReviewRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def enqueue(self, *, iso_year: int, iso_week: int, trigger: ReviewTrigger) -> WeeklyReview:
        validate_iso_week(iso_year, iso_week)
        row = WeeklyReviewRow(
            iso_year=iso_year, iso_week=iso_week, trigger=trigger, status=ReviewStatus.QUEUED
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as exc:
            raise ConflictError("Ya se está generando un borrador para esa semana") from exc
        self._session.refresh(row)
        return to_review(row)

    def find_by_id(self, review_id: int) -> WeeklyReview:
        return to_review(self._require(review_id))

    def find_all(
        self, *, iso_year: int | None = None, iso_week: int | None = None, limit: int = 20
    ) -> list[WeeklyReview]:
        stmt = select(WeeklyReviewRow).order_by(WeeklyReviewRow.id.desc()).limit(limit)
        if iso_year is not None:
            stmt = stmt.where(WeeklyReviewRow.iso_year == iso_year)
        if iso_week is not None:
            stmt = stmt.where(WeeklyReviewRow.iso_week == iso_week)
        return [to_review(row) for row in self._session.scalars(stmt)]

    def exists(self, *, iso_year: int, iso_week: int, trigger: ReviewTrigger) -> bool:
        stmt = select(WeeklyReviewRow.id).where(
            WeeklyReviewRow.iso_year == iso_year,
            WeeklyReviewRow.iso_week == iso_week,
            WeeklyReviewRow.trigger == trigger,
        )
        return self._session.scalar(stmt.limit(1)) is not None

    def claim_next(self) -> WeeklyReview | None:
        stmt = (
            select(WeeklyReviewRow)
            .where(WeeklyReviewRow.status == ReviewStatus.QUEUED)
            .order_by(WeeklyReviewRow.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        row = self._session.scalars(stmt).first()
        if row is None:
            return None
        row.status = ReviewStatus.RUNNING  # ORM rows are the mutable persistence boundary
        return self._flushed(row)

    def complete(self, review_id: int, result: ReviewResult) -> WeeklyReview:
        row = self._require(review_id)
        row.status = result.status
        row.as_of = result.as_of
        row.findings = [finding_to_json(item) for item in result.findings]
        row.rh_rows = [rh_row_to_json(item) for item in result.rh_rows]
        row.narrative = narrative_to_json(result.narrative) if result.narrative else None
        row.model = result.model
        row.input_tokens = result.input_tokens
        row.output_tokens = result.output_tokens
        row.error = _truncate(result.error)
        return self._flushed(row)

    def fail(self, review_id: int, error: str) -> WeeklyReview:
        row = self._require(review_id)
        row.status = ReviewStatus.FAILED
        row.error = _truncate(error)
        return self._flushed(row)

    def approve(self, review_id: int, approved_at: datetime) -> WeeklyReview:
        row = self._require(review_id)
        if row.status not in APPROVABLE:
            raise ConflictError("Solo se puede aprobar un borrador listo que no esté aprobado")
        row.status = ReviewStatus.APPROVED
        row.approved_at = approved_at
        return self._flushed(row)

    def fail_stale_running(self) -> int:
        stmt = (
            update(WeeklyReviewRow)
            .where(
                WeeklyReviewRow.status == ReviewStatus.RUNNING,
                WeeklyReviewRow.updated_at < func.now() - STALE_RUNNING_AFTER,
            )
            .values(status=ReviewStatus.FAILED, error=STALE_RUNNING_MESSAGE)
        )
        result = cast("CursorResult[Any]", self._session.execute(stmt))
        return result.rowcount

    def _flushed(self, row: WeeklyReviewRow) -> WeeklyReview:
        self._session.flush()
        return to_review(row)

    def _require(self, review_id: int) -> WeeklyReviewRow:
        row = self._session.get(WeeklyReviewRow, review_id)
        if row is None:
            raise NotFoundError("Borrador no encontrado")
        return row
