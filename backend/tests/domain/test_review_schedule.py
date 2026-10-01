from datetime import datetime

from tabernas.domain.review_schedule import Slot, last_due_slot, slot_to_enqueue
from tabernas.domain.review_types import ReviewTrigger

THU = ReviewTrigger.THURSDAY
MON = ReviewTrigger.MONDAY


def test_thursday_at_1730_reviews_the_current_week() -> None:
    assert last_due_slot(datetime(2026, 9, 24, 17, 30)) == Slot(
        THU, datetime(2026, 9, 24, 17, 30), 2026, 39
    )


def test_before_thursday_1730_the_last_slot_is_monday() -> None:
    assert last_due_slot(datetime(2026, 9, 24, 17, 29)) == Slot(
        MON, datetime(2026, 9, 21, 9, 0), 2026, 38
    )


def test_monday_at_nine_reviews_the_previous_week() -> None:
    assert last_due_slot(datetime(2026, 9, 28, 9, 0)) == Slot(
        MON, datetime(2026, 9, 28, 9, 0), 2026, 39
    )


def test_monday_before_nine_points_to_last_thursday() -> None:
    assert last_due_slot(datetime(2026, 9, 28, 8, 59)) == Slot(
        THU, datetime(2026, 9, 24, 17, 30), 2026, 39
    )


def test_catch_up_window_is_24_hours() -> None:
    assert slot_to_enqueue(datetime(2026, 9, 25, 17, 30)) is not None  # exactly 24 h late
    assert slot_to_enqueue(datetime(2026, 9, 25, 17, 31)) is None
    assert slot_to_enqueue(datetime(2026, 9, 28, 8, 59)) is None


def test_monday_after_new_year_reviews_week_53() -> None:
    # Review Focus #3: 2026 has 53 ISO weeks; 2027-01-04 is the first Monday of 2027.
    assert slot_to_enqueue(datetime(2027, 1, 4, 9, 30)) == Slot(
        MON, datetime(2027, 1, 4, 9, 0), 2026, 53
    )
