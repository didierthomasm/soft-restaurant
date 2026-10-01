"""Weekly review drafts (spec §5–§7): builds the context, runs the agent, stores the
snapshot and answers the detail view."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.pseudonyms import render
from tabernas.agents.weekly_review.agent import AgentOutcome, ReviewAgent
from tabernas.domain.periods import iso_week_range
from tabernas.domain.review import find_findings
from tabernas.domain.review_types import (
    REVIEW_HISTORY_WEEKS,
    Narrative,
    ReviewContext,
    ReviewResult,
    ReviewStatus,
    WeeklyReview,
    proposed_rows,
)
from tabernas.domain.types import Employee
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.review_settings import ReviewSettingsRepo
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.attendance import AttendanceService
from tabernas.sr.source import SR_UNAVAILABLE_MESSAGE, SrSource, SrUnavailableError

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
STALE_CHECK_STATUSES = frozenset(
    {ReviewStatus.READY, ReviewStatus.READY_NO_NARRATIVE, ReviewStatus.APPROVED}
)


@dataclass(frozen=True)
class ReviewDetail:
    review: WeeklyReview
    employees: tuple[Employee, ...]
    stale: bool | None


def build_context(
    session: Session, source: SrSource, clock: Clock, iso_year: int, iso_week: int
) -> ReviewContext:
    start, end = iso_week_range(iso_year, iso_week)
    attendance = AttendanceService(session, source, clock)
    week = attendance.build(start, end)
    history = attendance.build(
        start - timedelta(weeks=REVIEW_HISTORY_WEEKS), start - timedelta(days=1)
    )
    settings = ReviewSettingsRepo(session).get()
    findings = find_findings(week.results, history.results, week.warnings, settings, start, end)
    return ReviewContext(
        iso_year=iso_year,
        iso_week=iso_week,
        start=start,
        end=end,
        as_of=clock(),
        employees=tuple(EmployeeRepo(session).find_all()),
        week_results=week.results,
        history_results=history.results,
        rh_rows=proposed_rows(week.rh_rows),
        findings=tuple(findings),
    )


def run_review(
    factory: sessionmaker[Session],
    source: SrSource,
    clock: Clock,
    agent: ReviewAgent,
    review_id: int,
) -> WeeklyReview:
    with factory() as session:
        review = ReviewRepo(session).find_by_id(review_id)
        try:
            context = build_context(session, source, clock, review.iso_year, review.iso_week)
        except SrUnavailableError:
            logger.warning("Weekly review %s failed: SR unavailable", review_id)
            failed = ReviewRepo(session).fail(review_id, SR_UNAVAILABLE_MESSAGE)
            session.commit()
            return failed
    outcome = agent.run(context)  # may take a minute: no open transaction meanwhile
    with factory() as session:
        done = ReviewRepo(session).complete(review_id, to_result(context, outcome))
        session.commit()
    logger.info(
        "Weekly review %s: %s, %d findings, tokens in/out %d/%d",
        review_id,
        done.status,
        len(done.findings),
        outcome.input_tokens,
        outcome.output_tokens,
    )
    return done


def to_result(context: ReviewContext, outcome: AgentOutcome) -> ReviewResult:
    ready = outcome.narrative is not None
    return ReviewResult(
        status=ReviewStatus.READY if ready else ReviewStatus.READY_NO_NARRATIVE,
        as_of=context.as_of,
        findings=context.findings,
        rh_rows=context.rh_rows,
        narrative=outcome.narrative,
        model=outcome.model,
        input_tokens=outcome.input_tokens,
        output_tokens=outcome.output_tokens,
        error=outcome.error,
    )


def review_detail(session: Session, source: SrSource, clock: Clock, review_id: int) -> ReviewDetail:
    review = ReviewRepo(session).find_by_id(review_id)
    employees = tuple(EmployeeRepo(session).find_all())
    return ReviewDetail(
        review=review, employees=employees, stale=is_stale(session, source, clock, review)
    )


def is_stale(session: Session, source: SrSource, clock: Clock, review: WeeklyReview) -> bool | None:
    """True when today's findings or RH rows differ from the snapshot (spec §7.3)."""
    if review.status not in STALE_CHECK_STATUSES:
        return None
    try:
        current = build_context(session, source, clock, review.iso_year, review.iso_week)
    except SrUnavailableError:
        return None
    same_findings = [f.id for f in current.findings] == [f.id for f in review.findings]
    return not (same_findings and current.rh_rows == review.rh_rows)


def render_narrative(narrative: Narrative, employees: Sequence[Employee]) -> Narrative:
    return Narrative(
        summary=render(narrative.summary, employees),
        items=tuple(
            replace(item, explanation=render(item.explanation, employees))
            for item in narrative.items
        ),
    )
