from datetime import date

import pytest

from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    Finding,
    FindingKind,
    ProposedRhRow,
    ReviewSettings,
    proposed_rows,
    validate_review_settings,
)
from tabernas.domain.types import RhRow, RhType
from tabernas.domain.validation import DomainValidationError


def test_finding_kinds_are_listed_in_spec_order() -> None:
    assert list(FindingKind) == [
        FindingKind.REST_DAY_CHECKIN,
        FindingKind.ABSENT_NO_EXCEPTION,
        FindingKind.NO_CHECKIN_STREAK,
        FindingKind.REPEATED_LATE,
        FindingKind.CONFIG_WARNING,
    ]


def test_finding_fact_lookup() -> None:
    finding = Finding(
        id="X", kind=FindingKind.NO_CHECKIN_STREAK, employee_id=1, days=(), facts=(("days", 3),)
    )
    assert finding.fact("days") == 3
    assert finding.fact("missing") is None


def test_proposed_rows_drop_the_name() -> None:
    row = RhRow(
        employee_id=4, name="ALGUIEN", day=date(2026, 9, 23), rh_type=RhType.RETARDO, comment=""
    )
    assert proposed_rows([row]) == (
        ProposedRhRow(employee_id=4, day=date(2026, 9, 23), rh_type=RhType.RETARDO, comment=""),
    )


def test_default_and_boundary_review_settings_are_valid() -> None:
    validate_review_settings(DEFAULT_REVIEW_SETTINGS)
    validate_review_settings(ReviewSettings(streak_days=7, late_week=7, late_weeks=5))
    validate_review_settings(ReviewSettings(streak_days=1, late_week=1, late_weeks=1))


@pytest.mark.parametrize(
    ("settings", "message"),
    [
        (ReviewSettings(streak_days=0), "días seguidos sin checar"),
        (ReviewSettings(streak_days=8), "días seguidos sin checar"),
        (ReviewSettings(late_week=0), "retardos en la semana"),
        (ReviewSettings(late_weeks=6), "semanas con retardo"),
    ],
)
def test_out_of_range_review_settings_are_rejected(settings: ReviewSettings, message: str) -> None:
    with pytest.raises(DomainValidationError, match=message):
        validate_review_settings(settings)
