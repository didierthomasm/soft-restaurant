from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import AgentOutcome
from tabernas.agents.weekly_review.fake import FakeReviewAgent
from tabernas.domain.review_types import FindingKind, ReviewContext, ReviewStatus, ReviewTrigger
from tabernas.domain.types import Employee, Incident
from tabernas.repos.employees import EmployeeRepo
from tabernas.repos.justifications import JustificationRepo
from tabernas.repos.rest_rules import RestRuleRepo
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import build_context, render_narrative, review_detail, run_review
from tabernas.sr.source import SR_UNAVAILABLE_MESSAGE, SrCheckin, SrUnavailableError
from tests.repos.helpers import make_employee
from tests.support import StubSource

Factory = sessionmaker[Session]
NOW = datetime(2026, 9, 27, 20, 0)  # Sunday evening of 2026-W39
HISTORY_START = date(2026, 7, 27)  # 8 weeks before 2026-09-21
EXPECTED_KINDS = [
    FindingKind.REST_DAY_CHECKIN,  # Tue 22 is his rest day and he checked in
    FindingKind.ABSENT_NO_EXCEPTION,  # Mon 21
    FindingKind.NO_CHECKIN_STREAK,  # Fri 25 – Sun 27
    FindingKind.CONFIG_WARNING,  # MISSING_RH_NAME
]


def clock() -> datetime:
    return NOW


def setup_employee(factory: Factory) -> Employee:
    with factory() as session:
        employee = make_employee(session, 7, short_name="EMPLEADO G")
        RestRuleRepo(session).create(
            employee_id=employee.id,
            fixed_weekday=1,  # Tuesday
            extra_weekday=0,  # Monday, only in double-rest weeks (not W39)
            double_rest_anchor=date(2026, 9, 28),
            valid_from=date(2026, 1, 1),
            valid_to=None,
        )
        session.commit()
        return employee


def checkins() -> StubSource:
    history = [
        SrCheckin(sr_id=7, at=datetime.combine(HISTORY_START + timedelta(days=d), time(16, 30)))
        for d in range(56)
    ]
    week = [
        SrCheckin(sr_id=7, at=datetime(2026, 9, 22, 16, 45)),  # rest day
        SrCheckin(sr_id=7, at=datetime(2026, 9, 23, 16, 51)),  # late (single: no finding)
        SrCheckin(sr_id=7, at=datetime(2026, 9, 24, 16, 40)),  # on time
    ]
    return StubSource(checkins=history + week)


def enqueue(factory: Factory) -> int:
    with factory() as session:
        review = ReviewRepo(session).enqueue(
            iso_year=2026, iso_week=39, trigger=ReviewTrigger.MANUAL
        )
        session.commit()
        return review.id


class NoNarrativeAgent:
    def run(self, context: ReviewContext) -> AgentOutcome:
        return AgentOutcome(None, "La API de Claude respondió con error 500.", "claude-opus-5-5")


def test_build_context_collects_week_history_and_findings(session_factory: Factory) -> None:
    employee = setup_employee(session_factory)
    with session_factory() as session:
        context = build_context(session, checkins(), clock, 2026, 39)
    assert [f.kind for f in context.findings] == EXPECTED_KINDS
    assert context.as_of == NOW
    assert min(r.day for r in context.history_results) == HISTORY_START
    assert max(r.day for r in context.history_results) == date(2026, 9, 20)
    assert [row.day.day for row in context.rh_rows] == [21, 23, 25, 26, 27]
    assert context.employees == (employee,)


def test_run_review_stores_a_ready_snapshot(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    done = run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    assert done.status == ReviewStatus.READY
    assert [f.kind for f in done.findings] == EXPECTED_KINDS
    assert done.narrative is not None and len(done.narrative.items) == len(EXPECTED_KINDS)
    assert (done.as_of, done.model) == (NOW, "fake")
    with session_factory() as session:
        assert ReviewRepo(session).find_by_id(review_id) == done


def test_agent_failure_keeps_findings_without_narrative(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    done = run_review(session_factory, checkins(), clock, NoNarrativeAgent(), review_id)
    assert done.status == ReviewStatus.READY_NO_NARRATIVE
    assert done.error == "La API de Claude respondió con error 500."
    assert len(done.findings) == len(EXPECTED_KINDS) and len(done.rh_rows) == 5


def test_sr_unavailable_fails_the_review(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    source = StubSource(error=SrUnavailableError("down"))
    done = run_review(session_factory, source, clock, FakeReviewAgent(), review_id)
    assert (done.status, done.error) == (ReviewStatus.FAILED, SR_UNAVAILABLE_MESSAGE)


def test_detail_flags_stale_data_after_a_justification(session_factory: Factory) -> None:
    employee = setup_employee(session_factory)
    review_id = enqueue(session_factory)
    source = checkins()
    run_review(session_factory, source, clock, FakeReviewAgent(), review_id)
    with session_factory() as session:
        assert review_detail(session, source, clock, review_id).stale is False
        JustificationRepo(session).create(
            employee_id=employee.id,
            day=date(2026, 9, 21),
            incident=Incident.ABSENT,
            reason="Enfermo",
        )
        assert review_detail(session, source, clock, review_id).stale is True


def test_no_stale_flag_before_running_or_without_sr(session_factory: Factory) -> None:
    setup_employee(session_factory)
    review_id = enqueue(session_factory)
    with session_factory() as session:
        assert review_detail(session, checkins(), clock, review_id).stale is None
    run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    down = StubSource(error=SrUnavailableError("down"))
    with session_factory() as session:
        assert review_detail(session, down, clock, review_id).stale is None


def test_detail_renders_names_of_deactivated_employees(session_factory: Factory) -> None:
    # Review Focus #5
    employee = setup_employee(session_factory)
    review_id = enqueue(session_factory)
    run_review(session_factory, checkins(), clock, FakeReviewAgent(), review_id)
    with session_factory() as session:
        EmployeeRepo(session).update(employee.id, {"active": False})
        session.commit()
        detail = review_detail(session, checkins(), clock, review_id)
    assert detail.review.narrative is not None
    rendered = render_narrative(detail.review.narrative, detail.employees)
    assert rendered.items[0].explanation.startswith("EMPLEADO G")
    assert "{E" not in rendered.summary + "".join(i.explanation for i in rendered.items)
