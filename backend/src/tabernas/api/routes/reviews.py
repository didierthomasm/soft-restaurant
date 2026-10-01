"""Weekly review drafts (spec §7.2). The API only enqueues and reads; the worker runs them."""

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from tabernas.api.deps import ClockDep, SessionDep, SrSourceDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.review_types import (
    FindingKind,
    Narrative,
    Priority,
    ReviewStatus,
    ReviewTrigger,
    SuggestedAction,
    WeeklyReview,
)
from tabernas.domain.types import Employee, RhType
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import ReviewDetail, render_narrative, review_detail

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    week: int = Field(ge=1, le=53)


class ReviewSummaryOut(BaseModel):
    id: int
    year: int
    week: int
    trigger: ReviewTrigger
    status: ReviewStatus
    created_at: datetime
    as_of: datetime | None
    approved_at: datetime | None
    error: str | None


class FindingOut(BaseModel):
    id: str
    kind: FindingKind
    employee_id: int | None
    employee_name: str | None
    days: list[date]
    facts: dict[str, int | str]


class NarrativeItemOut(BaseModel):
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


class NarrativeOut(BaseModel):
    summary: str
    items: list[NarrativeItemOut]


class ProposedRowOut(BaseModel):
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str


class ReviewDetailOut(ReviewSummaryOut):
    findings: list[FindingOut]
    narrative: NarrativeOut | None
    rh_rows: list[ProposedRowOut]
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    stale: bool | None


def summary_out(review: WeeklyReview) -> ReviewSummaryOut:
    return ReviewSummaryOut(
        id=review.id,
        year=review.iso_year,
        week=review.iso_week,
        trigger=review.trigger,
        status=review.status,
        created_at=review.created_at,
        as_of=review.as_of,
        approved_at=review.approved_at,
        error=review.error,
    )


def _short_name(by_id: Mapping[int, Employee], employee_id: int | None) -> str | None:
    employee = by_id.get(employee_id) if employee_id is not None else None
    return employee.short_name if employee else None


def _rh_name(by_id: Mapping[int, Employee], employee_id: int) -> str:
    employee = by_id.get(employee_id)
    if employee is None:
        return f"Empleado {employee_id}"
    return employee.rh_name or employee.short_name


def _narrative_out(
    narrative: Narrative | None, employees: Sequence[Employee]
) -> NarrativeOut | None:
    if narrative is None:
        return None
    rendered = render_narrative(narrative, employees)
    items = [
        NarrativeItemOut(
            finding_id=item.finding_id,
            priority=item.priority,
            explanation=item.explanation,
            suggested_action=item.suggested_action,
        )
        for item in rendered.items
    ]
    return NarrativeOut(summary=rendered.summary, items=items)


def detail_out(detail: ReviewDetail) -> ReviewDetailOut:
    review = detail.review
    by_id = {employee.id: employee for employee in detail.employees}
    findings = [
        FindingOut(
            id=f.id,
            kind=f.kind,
            employee_id=f.employee_id,
            employee_name=_short_name(by_id, f.employee_id),
            days=list(f.days),
            facts=dict(f.facts),
        )
        for f in review.findings
    ]
    rows = [
        ProposedRowOut(
            employee_id=r.employee_id,
            name=_rh_name(by_id, r.employee_id),
            day=r.day,
            rh_type=r.rh_type,
            comment=r.comment,
        )
        for r in review.rh_rows
    ]
    return ReviewDetailOut(
        **summary_out(review).model_dump(),
        findings=findings,
        narrative=_narrative_out(review.narrative, detail.employees),
        rh_rows=sorted(rows, key=lambda row: (row.name, row.day)),
        model=review.model,
        input_tokens=review.input_tokens,
        output_tokens=review.output_tokens,
        stale=detail.stale,
    )


@router.post("", status_code=202)
def create_review(body: ReviewCreate, session: SessionDep) -> Envelope[ReviewSummaryOut]:
    review = ReviewRepo(session).enqueue(
        iso_year=body.year, iso_week=body.week, trigger=ReviewTrigger.MANUAL
    )
    return ok(summary_out(review))


@router.get("")
def list_reviews(
    session: SessionDep,
    year: Annotated[int | None, Query()] = None,
    week: Annotated[int | None, Query()] = None,
) -> Envelope[list[ReviewSummaryOut]]:
    if (year is None) != (week is None):
        raise DomainValidationError("Indica año y semana juntos, o ninguno")
    reviews = ReviewRepo(session).find_all(iso_year=year, iso_week=week)
    return ok([summary_out(review) for review in reviews])


@router.get("/{review_id}")
def get_review(
    review_id: int, session: SessionDep, source: SrSourceDep, clock: ClockDep
) -> Envelope[ReviewDetailOut]:
    return ok(detail_out(review_detail(session, source, clock, review_id)))


@router.post("/{review_id}/approve")
def approve_review(
    review_id: int, session: SessionDep, clock: ClockDep
) -> Envelope[ReviewSummaryOut]:
    return ok(summary_out(ReviewRepo(session).approve(review_id, clock())))
