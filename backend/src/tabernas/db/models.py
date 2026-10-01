"""SQLAlchemy tables for our own configuration. Derived attendance is never
stored; weekly review drafts are the one dated snapshot (stage 2, spec E7)."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    MetaData,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from tabernas.domain.review_types import ReviewStatus, ReviewTrigger
from tabernas.domain.types import Area, ExceptionKind, Incident, RhType

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enum(enum_cls: type) -> SAEnum:
    return SAEnum(enum_cls, native_enum=False, length=32, validate_strings=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmployeeRow(TimestampMixin, Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(primary_key=True)
    sr_id: Mapped[int | None] = mapped_column(unique=True)
    short_name: Mapped[str] = mapped_column(String(80))
    rh_name: Mapped[str | None] = mapped_column(String(160))
    area: Mapped[Area] = mapped_column(_enum(Area))
    applies_lateness: Mapped[bool]
    tracks_attendance: Mapped[bool]
    active: Mapped[bool] = mapped_column(default=True)


class RestRuleRow(TimestampMixin, Base):
    __tablename__ = "rest_rule"
    __table_args__ = (
        CheckConstraint("fixed_weekday BETWEEN 0 AND 6", name="fixed_weekday_range"),
        CheckConstraint("extra_weekday BETWEEN 0 AND 6", name="extra_weekday_range"),
        CheckConstraint("fixed_weekday <> extra_weekday", name="distinct_weekdays"),
        CheckConstraint("valid_to IS NULL OR valid_from <= valid_to", name="valid_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    fixed_weekday: Mapped[int] = mapped_column(SmallInteger)
    extra_weekday: Mapped[int] = mapped_column(SmallInteger)
    double_rest_anchor: Mapped[date]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]


class ScheduleExceptionRow(TimestampMixin, Base):
    __tablename__ = "schedule_exception"
    __table_args__ = (
        CheckConstraint("date_from <= date_to", name="date_range"),
        CheckConstraint(
            "(employee_id IS NULL) = (kind = 'STORE_CLOSED')", name="closure_has_no_employee"
        ),
        CheckConstraint(
            "(rh_type IS NOT NULL) = (kind = 'WORK_TO_ABSENCE')", name="absence_has_rh_type"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ExceptionKind] = mapped_column(_enum(ExceptionKind))
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    date_from: Mapped[date]
    date_to: Mapped[date]
    rh_type: Mapped[RhType | None] = mapped_column(_enum(RhType))
    comment: Mapped[str] = mapped_column(String(500), default="")


class JustificationRow(TimestampMixin, Base):
    __tablename__ = "justification"
    __table_args__ = (UniqueConstraint("employee_id", "day", "incident"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employee.id", ondelete="CASCADE"), index=True
    )
    day: Mapped[date]
    incident: Mapped[Incident] = mapped_column(_enum(Incident))
    reason: Mapped[str] = mapped_column(String(500))
    rh_type: Mapped[RhType] = mapped_column(_enum(RhType))


class SettingRow(TimestampMixin, Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(64))


class WeeklyReviewRow(TimestampMixin, Base):
    __tablename__ = "weekly_review"
    __table_args__ = (
        CheckConstraint("iso_week BETWEEN 1 AND 53", name="iso_week_range"),
        Index(
            "uq_weekly_review_in_progress",
            "iso_year",
            "iso_week",
            unique=True,
            postgresql_where=text("status IN ('QUEUED', 'RUNNING')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    iso_year: Mapped[int]
    iso_week: Mapped[int] = mapped_column(SmallInteger)
    trigger: Mapped[ReviewTrigger] = mapped_column(_enum(ReviewTrigger))
    status: Mapped[ReviewStatus] = mapped_column(_enum(ReviewStatus))
    as_of: Mapped[datetime | None] = mapped_column(DateTime())  # naive business time
    findings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    rh_rows: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    narrative: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(64))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(String(1000))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime())  # naive business time
