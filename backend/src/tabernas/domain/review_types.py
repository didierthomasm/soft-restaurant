"""Weekly review types (stage 2). Pure data: no database, no HTTP, no Claude."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum

from tabernas.domain.types import DayResult, Employee, RhRow, RhType
from tabernas.domain.validation import DomainValidationError

REVIEW_HISTORY_WEEKS = 8  # weeks of history the agent may look at (get_employee_history)


class FindingKind(StrEnum):
    """Declaration order is the order findings are listed in (spec §4)."""

    REST_DAY_CHECKIN = "REST_DAY_CHECKIN"
    ABSENT_NO_EXCEPTION = "ABSENT_NO_EXCEPTION"
    NO_CHECKIN_STREAK = "NO_CHECKIN_STREAK"
    REPEATED_LATE = "REPEATED_LATE"
    CONFIG_WARNING = "CONFIG_WARNING"


class Priority(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SuggestedAction(StrEnum):
    JUSTIFY = "JUSTIFY"
    REST_SWAP = "REST_SWAP"
    ADD_EXCEPTION = "ADD_EXCEPTION"
    FIX_CONFIG = "FIX_CONFIG"
    NONE = "NONE"


class ReviewStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    READY = "READY"
    READY_NO_NARRATIVE = "READY_NO_NARRATIVE"
    FAILED = "FAILED"
    APPROVED = "APPROVED"


class ReviewTrigger(StrEnum):
    THURSDAY = "THURSDAY"
    MONDAY = "MONDAY"
    MANUAL = "MANUAL"


Fact = tuple[str, int | str]


@dataclass(frozen=True)
class Finding:
    id: str
    kind: FindingKind
    employee_id: int | None
    days: tuple[date, ...]
    facts: tuple[Fact, ...] = ()

    def fact(self, key: str) -> int | str | None:
        return dict(self.facts).get(key)


@dataclass(frozen=True)
class NarrativeItem:
    finding_id: str
    priority: Priority
    explanation: str
    suggested_action: SuggestedAction


@dataclass(frozen=True)
class Narrative:
    summary: str
    items: tuple[NarrativeItem, ...]


@dataclass(frozen=True)
class ProposedRhRow:
    """An RH row without the employee's name: names are rendered when the draft is served."""

    employee_id: int
    day: date
    rh_type: RhType
    comment: str


def proposed_rows(rows: Sequence[RhRow]) -> tuple[ProposedRhRow, ...]:
    return tuple(ProposedRhRow(r.employee_id, r.day, r.rh_type, r.comment) for r in rows)


@dataclass(frozen=True)
class ReviewSettings:
    streak_days: int = 2  # consecutive unjustified absences that make a streak
    late_week: int = 2  # unjustified lates in the reviewed week
    late_weeks: int = 3  # weeks with any late among the reviewed week and the 4 before


DEFAULT_REVIEW_SETTINGS = ReviewSettings()
REVIEW_SETTING_LIMITS = {"streak_days": 7, "late_week": 7, "late_weeks": 5}
_SETTING_LABELS = {
    "streak_days": "días seguidos sin checar",
    "late_week": "retardos en la semana",
    "late_weeks": "semanas con retardo",
}


def validate_review_settings(settings: ReviewSettings) -> None:
    for field, maximum in REVIEW_SETTING_LIMITS.items():
        value = getattr(settings, field)
        if not 1 <= value <= maximum:
            raise DomainValidationError(
                f"El umbral de {_SETTING_LABELS[field]} debe estar entre 1 y {maximum}"
            )


@dataclass(frozen=True)
class ReviewContext:
    """Everything the agent may see about one week, computed once by the service."""

    iso_year: int
    iso_week: int
    start: date
    end: date
    as_of: datetime
    employees: tuple[Employee, ...]  # all employees, active or not (pseudonyms, scrub)
    week_results: tuple[DayResult, ...]
    history_results: tuple[DayResult, ...]  # REVIEW_HISTORY_WEEKS weeks before `start`
    rh_rows: tuple[ProposedRhRow, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ReviewResult:
    status: ReviewStatus
    as_of: datetime
    findings: tuple[Finding, ...]
    rh_rows: tuple[ProposedRhRow, ...]
    narrative: Narrative | None
    model: str | None
    input_tokens: int
    output_tokens: int
    error: str | None


@dataclass(frozen=True)
class WeeklyReview:
    id: int
    iso_year: int
    iso_week: int
    trigger: ReviewTrigger
    status: ReviewStatus
    created_at: datetime
    as_of: datetime | None = None
    findings: tuple[Finding, ...] = ()
    rh_rows: tuple[ProposedRhRow, ...] = ()
    narrative: Narrative | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    approved_at: datetime | None = None
