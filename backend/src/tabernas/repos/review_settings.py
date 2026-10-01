"""Weekly-review thresholds, stored in the setting table as review_<field> keys."""

from dataclasses import asdict, fields

from sqlalchemy import select
from sqlalchemy.orm import Session

from tabernas.db.models import SettingRow
from tabernas.domain.review_types import (
    DEFAULT_REVIEW_SETTINGS,
    ReviewSettings,
    validate_review_settings,
)

KEY_PREFIX = "review_"


def setting_key(field: str) -> str:
    return f"{KEY_PREFIX}{field}"


class ReviewSettingsRepo:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> ReviewSettings:
        keys = [setting_key(f.name) for f in fields(ReviewSettings)]
        stmt = select(SettingRow.key, SettingRow.value).where(SettingRow.key.in_(keys))
        stored: dict[str, str] = {key: value for key, value in self._session.execute(stmt).all()}
        values = {
            name: int(stored[setting_key(name)]) if setting_key(name) in stored else default
            for name, default in asdict(DEFAULT_REVIEW_SETTINGS).items()
        }
        return ReviewSettings(**values)

    def save(self, settings: ReviewSettings) -> ReviewSettings:
        validate_review_settings(settings)
        for name, value in asdict(settings).items():
            self._session.merge(SettingRow(key=setting_key(name), value=str(value)))
        self._session.flush()
        return self.get()
