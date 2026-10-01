"""Background worker (spec §6): schedules weekly reviews and runs queued ones.

Run with `python -m tabernas.worker` (compose service `worker`). It is the only process
that executes reviews; the API only enqueues them."""

import logging
import time
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

from tabernas.agents.weekly_review.agent import ReviewAgent
from tabernas.agents.weekly_review.factory import build_review_agent
from tabernas.config import get_settings
from tabernas.db.session import make_engine, make_session_factory
from tabernas.domain.review_schedule import slot_to_enqueue
from tabernas.domain.review_types import WeeklyReview
from tabernas.main import local_clock
from tabernas.repos.errors import ConflictError
from tabernas.repos.reviews import ReviewRepo
from tabernas.services.review import run_review
from tabernas.sr import build_sr_source
from tabernas.sr.source import SrSource

logger = logging.getLogger("tabernas.worker")

POLL_SECONDS = 10
INTERNAL_ERROR_MESSAGE = "Error interno al generar el borrador; revisa los logs del worker."
Factory = sessionmaker[Session]
Clock = Callable[[], datetime]


def schedule_due(factory: Factory, clock: Clock) -> WeeklyReview | None:
    slot = slot_to_enqueue(clock())
    if slot is None:
        return None
    with factory() as session:
        repo = ReviewRepo(session)
        if repo.exists(iso_year=slot.iso_year, iso_week=slot.iso_week, trigger=slot.trigger):
            return None
        try:
            review = repo.enqueue(
                iso_year=slot.iso_year, iso_week=slot.iso_week, trigger=slot.trigger
            )
        except ConflictError:
            return None  # a manual run of that week is in progress; next tick retries
        session.commit()
    logger.info("Enqueued %s review for %s-W%02d", slot.trigger, slot.iso_year, slot.iso_week)
    return review


def fail_stale(factory: Factory) -> int:
    with factory() as session:
        count = ReviewRepo(session).fail_stale_running()
        session.commit()
    if count:
        logger.warning("Marked %d interrupted review(s) as failed", count)
    return count


def run_next(
    factory: Factory, source: SrSource, clock: Clock, agent: ReviewAgent
) -> WeeklyReview | None:
    with factory() as session:
        claimed = ReviewRepo(session).claim_next()
        session.commit()
    if claimed is None:
        return None
    try:
        return run_review(factory, source, clock, agent, claimed.id)
    except Exception:
        logger.exception("Weekly review %s failed unexpectedly", claimed.id)
        with factory() as session:
            failed = ReviewRepo(session).fail(claimed.id, INTERNAL_ERROR_MESSAGE)
            session.commit()
        return failed


def tick(factory: Factory, source: SrSource, clock: Clock, agent: ReviewAgent) -> None:
    fail_stale(factory)
    schedule_due(factory, clock)
    while run_next(factory, source, clock, agent) is not None:
        continue


def main() -> None:  # pragma: no cover - process entry point, exercised through compose
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()
    factory = make_session_factory(make_engine(settings.database_url))
    source = build_sr_source(settings)
    clock = local_clock(settings.app_timezone)
    agent = build_review_agent(settings)
    logger.info("Worker started (review agent: %s)", settings.review_agent)
    while True:
        try:
            tick(factory, source, clock, agent)
        except Exception:
            logger.exception("Worker tick failed; retrying in %ss", POLL_SECONDS)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":  # pragma: no cover
    main()
