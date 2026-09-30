from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from tabernas.api.deps import SessionDep
from tabernas.api.envelope import Envelope, ok
from tabernas.domain.types import AttendanceSettings
from tabernas.domain.validation import MAX_TOLERANCE_MINUTES, format_hhmm, parse_hhmm
from tabernas.repos.settings import SettingsRepo

router = APIRouter(prefix="/settings", tags=["settings"])

HHMM = Annotated[str, Field(pattern=r"^\d{2}:\d{2}$", examples=["16:40"])]


class SettingsBody(BaseModel):
    entry_time_kitchen: HHMM
    entry_time_other: HHMM
    tolerance_minutes: int = Field(ge=0, le=MAX_TOLERANCE_MINUTES)


def _body(settings: AttendanceSettings) -> SettingsBody:
    return SettingsBody(
        entry_time_kitchen=format_hhmm(settings.entry_time_kitchen),
        entry_time_other=format_hhmm(settings.entry_time_other),
        tolerance_minutes=settings.tolerance_minutes,
    )


@router.get("")
def read_settings(session: SessionDep) -> Envelope[SettingsBody]:
    return ok(_body(SettingsRepo(session).get()))


@router.put("")
def write_settings(body: SettingsBody, session: SessionDep) -> Envelope[SettingsBody]:
    wanted = AttendanceSettings(
        entry_time_kitchen=parse_hhmm(body.entry_time_kitchen),
        entry_time_other=parse_hhmm(body.entry_time_other),
        tolerance_minutes=body.tolerance_minutes,
    )
    return ok(_body(SettingsRepo(session).save(wanted)))
