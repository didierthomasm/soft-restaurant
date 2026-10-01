"""When the weekly review runs (spec §6.2): Thursday 17:30 reviews the current ISO week,
Monday 09:00 the previous one. A slot missed while the Mac slept runs within 24 hours."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from tabernas.domain.periods import week_monday
from tabernas.domain.review_types import ReviewTrigger

THURSDAY_AT = time(17, 30)
MONDAY_AT = time(9, 0)
CATCH_UP_WINDOW = timedelta(hours=24)


@dataclass(frozen=True)
class Slot:
    trigger: ReviewTrigger
    due_at: datetime
    iso_year: int
    iso_week: int


def _slot(trigger: ReviewTrigger, due_at: datetime, reviewed_day: date) -> Slot:
    year, week, _ = reviewed_day.isocalendar()
    return Slot(trigger, due_at, year, week)


def last_due_slot(now: datetime) -> Slot:
    monday = week_monday(now.date())
    previous_monday = monday - timedelta(weeks=1)
    candidates = (
        _slot(
            ReviewTrigger.THURSDAY,
            datetime.combine(monday + timedelta(days=3), THURSDAY_AT),
            monday,
        ),
        _slot(ReviewTrigger.MONDAY, datetime.combine(monday, MONDAY_AT), previous_monday),
        _slot(
            ReviewTrigger.THURSDAY,
            datetime.combine(previous_monday + timedelta(days=3), THURSDAY_AT),
            previous_monday,
        ),
    )
    return max((s for s in candidates if s.due_at <= now), key=lambda s: s.due_at)


def slot_to_enqueue(now: datetime) -> Slot | None:
    slot = last_due_slot(now)
    return slot if now - slot.due_at <= CATCH_UP_WINDOW else None
