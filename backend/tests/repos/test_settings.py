from datetime import time

import pytest
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.types import DEFAULT_SETTINGS, AttendanceSettings
from tabernas.domain.validation import DomainValidationError
from tabernas.repos.settings import SettingsRepo


def test_empty_table_returns_defaults(session: Session) -> None:
    # Review Focus #5: a database created without the seed must still work.
    assert SettingsRepo(session).get() == DEFAULT_SETTINGS


def test_partial_rows_are_filled_with_defaults(session: Session) -> None:
    session.add(SettingRow(key="tolerance_minutes", value="5"))
    session.flush()
    settings = SettingsRepo(session).get()
    assert settings.tolerance_minutes == 5
    assert settings.entry_time_other == DEFAULT_SETTINGS.entry_time_other


def test_save_round_trip(session: Session) -> None:
    wanted = AttendanceSettings(time(16, 0), time(16, 15), 5)
    assert SettingsRepo(session).save(wanted) == wanted
    assert SettingsRepo(session).get() == wanted


def test_save_rejects_bad_tolerance(session: Session) -> None:
    with pytest.raises(DomainValidationError):
        SettingsRepo(session).save(AttendanceSettings(time(16, 0), time(16, 15), 90))
