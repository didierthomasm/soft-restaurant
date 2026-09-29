"""Attendance domain types. Pure data: no database, no HTTP."""

from dataclasses import dataclass
from datetime import date, datetime, time
from enum import StrEnum


class Area(StrEnum):
    KITCHEN = "KITCHEN"
    OTHER = "OTHER"


class RhType(StrEnum):
    """Incident types of the HR tool, plus NO_CAPTURAR (justified, not reported)."""

    RETARDO = "RETARDO"
    FALTA_INJUSTIFICADA = "FALTA_INJUSTIFICADA"
    FALTA_JUSTIFICADA = "FALTA_JUSTIFICADA"
    VACACIONES = "VACACIONES"
    INCAPACIDAD = "INCAPACIDAD"
    PERMISO = "PERMISO"
    DESCANSO = "DESCANSO"
    NO_CAPTURAR = "NO_CAPTURAR"


class ExceptionKind(StrEnum):
    STORE_CLOSED = "STORE_CLOSED"
    PRESENT_NO_CHECKIN = "PRESENT_NO_CHECKIN"
    REST_TO_WORK = "REST_TO_WORK"
    WORK_TO_ABSENCE = "WORK_TO_ABSENCE"
    MANUAL_ABSENCE = "MANUAL_ABSENCE"


class Incident(StrEnum):
    LATE = "LATE"
    ABSENT = "ABSENT"


class Planned(StrEnum):
    WORK = "WORK"
    REST = "REST"
    CLOSED = "CLOSED"
    ABSENCE = "ABSENCE"


class Outcome(StrEnum):
    OK = "OK"
    LATE = "LATE"
    ABSENT = "ABSENT"
    UNREGISTERED_CHANGE = "UNREGISTERED_CHANGE"
    REST = "REST"
    CLOSED = "CLOSED"
    JUSTIFIED = "JUSTIFIED"
    PENDING = "PENDING"
    FUTURE = "FUTURE"


class WarningCode(StrEnum):
    NO_REST_RULE = "NO_REST_RULE"
    UNMAPPED_CHECKIN = "UNMAPPED_CHECKIN"
    ORPHAN_JUSTIFICATION = "ORPHAN_JUSTIFICATION"
    MISSING_RH_NAME = "MISSING_RH_NAME"


@dataclass(frozen=True)
class Employee:
    id: int
    sr_id: int | None
    short_name: str
    rh_name: str | None
    area: Area
    applies_lateness: bool
    tracks_attendance: bool
    active: bool


@dataclass(frozen=True)
class RestRule:
    id: int
    employee_id: int
    fixed_weekday: int  # date.weekday(): 0 = Monday ... 6 = Sunday
    extra_weekday: int
    double_rest_anchor: date  # Monday of a week with double rest
    valid_from: date
    valid_to: date | None


@dataclass(frozen=True)
class ScheduleException:
    id: int
    kind: ExceptionKind
    employee_id: int | None  # None only for STORE_CLOSED
    date_from: date
    date_to: date
    rh_type: RhType | None  # set only for WORK_TO_ABSENCE
    comment: str


@dataclass(frozen=True)
class Justification:
    id: int
    employee_id: int
    day: date
    incident: Incident
    reason: str
    rh_type: RhType


@dataclass(frozen=True)
class Checkin:
    sr_id: int
    at: datetime  # naive, SR local time


@dataclass(frozen=True)
class AttendanceSettings:
    entry_time_kitchen: time
    entry_time_other: time
    tolerance_minutes: int

    def entry_time(self, area: Area) -> time:
        return self.entry_time_kitchen if area == Area.KITCHEN else self.entry_time_other


DEFAULT_SETTINGS = AttendanceSettings(
    entry_time_kitchen=time(16, 30), entry_time_other=time(16, 40), tolerance_minutes=10
)


@dataclass(frozen=True)
class PlannedDay:
    employee_id: int
    day: date
    planned: Planned
    rh_type: RhType | None = None
    present_no_checkin: bool = False
    manual_absence: bool = False
    comment: str = ""


@dataclass(frozen=True)
class DayResult:
    employee_id: int
    day: date
    planned: Planned
    outcome: Outcome
    checkin: datetime | None = None
    minutes_late: int | None = None
    rh_type: RhType | None = None
    justification_id: int | None = None
    comment: str = ""


@dataclass(frozen=True)
class AttendanceWarning:
    code: WarningCode
    employee_id: int | None
    day: date | None
    detail: str


@dataclass(frozen=True)
class RhRow:
    employee_id: int
    name: str
    day: date
    rh_type: RhType
    comment: str
