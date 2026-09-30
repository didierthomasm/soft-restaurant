"""Attendance settings stored as key/value rows; missing keys fall back to defaults."""

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.types import DEFAULT_SETTINGS, AttendanceSettings
from tabernas.domain.validation import format_hhmm, parse_hhmm, validate_tolerance


def serialize_settings(settings: AttendanceSettings) -> dict[str, str]:
    return {
        "entry_time_kitchen": format_hhmm(settings.entry_time_kitchen),
        "entry_time_other": format_hhmm(settings.entry_time_other),
        "tolerance_minutes": str(settings.tolerance_minutes),
    }


def deserialize_settings(values: Mapping[str, str]) -> AttendanceSettings:
    return AttendanceSettings(
        entry_time_kitchen=parse_hhmm(values["entry_time_kitchen"]),
        entry_time_other=parse_hhmm(values["entry_time_other"]),
        tolerance_minutes=int(values["tolerance_minutes"]),
    )


class SettingsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> AttendanceSettings:
        stored = dict(self._session.execute(select(SettingRow.key, SettingRow.value)).all())
        return deserialize_settings({**serialize_settings(DEFAULT_SETTINGS), **stored})

    def save(self, settings: AttendanceSettings) -> AttendanceSettings:
        validate_tolerance(settings.tolerance_minutes)
        for key, value in serialize_settings(settings).items():
            self._session.merge(SettingRow(key=key, value=value))
        self._session.flush()
        return self.get()
