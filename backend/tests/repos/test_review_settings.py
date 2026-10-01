import pytest
from sqlalchemy.orm import Session

from tabernas.domain.review_types import DEFAULT_REVIEW_SETTINGS, ReviewSettings
from tabernas.domain.types import DEFAULT_SETTINGS
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.review_settings import ReviewSettingsRepo
from tabernas.repos.settings import SettingsRepo


def test_empty_table_returns_defaults(session: Session) -> None:
    assert ReviewSettingsRepo(session).get() == DEFAULT_REVIEW_SETTINGS


def test_save_round_trip(session: Session) -> None:
    wanted = ReviewSettings(streak_days=3, late_week=1, late_weeks=4)
    assert ReviewSettingsRepo(session).save(wanted) == wanted
    assert ReviewSettingsRepo(session).get() == wanted


def test_review_keys_do_not_disturb_attendance_settings(session: Session) -> None:
    ReviewSettingsRepo(session).save(ReviewSettings(streak_days=3, late_week=1, late_weeks=4))
    assert SettingsRepo(session).get() == DEFAULT_SETTINGS


def test_invalid_values_are_rejected_before_writing(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        ReviewSettingsRepo(session).save(ReviewSettings(streak_days=0))
    assert ReviewSettingsRepo(session).get() == DEFAULT_REVIEW_SETTINGS
