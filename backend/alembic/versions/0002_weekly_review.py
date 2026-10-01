"""weekly review

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-01 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REVIEW_SETTINGS = [
    {"key": "review_streak_days", "value": "2"},
    {"key": "review_late_week", "value": "2"},
    {"key": "review_late_weeks", "value": "3"},
]


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "weekly_review",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("iso_year", sa.Integer(), nullable=False),
        sa.Column("iso_week", sa.SmallInteger(), nullable=False),
        sa.Column(
            "trigger",
            sa.Enum(
                "THURSDAY", "MONDAY", "MANUAL", name="reviewtrigger", native_enum=False, length=32
            ),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "READY",
                "READY_NO_NARRATIVE",
                "FAILED",
                "APPROVED",
                name="reviewstatus",
                native_enum=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("rh_rows", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("narrative", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "iso_week BETWEEN 1 AND 53", name=op.f("ck_weekly_review_iso_week_range")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_weekly_review")),
    )
    op.create_index(
        "uq_weekly_review_in_progress",
        "weekly_review",
        ["iso_year", "iso_week"],
        unique=True,
        postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"),
    )
    setting = sa.table("setting", sa.column("key", sa.String), sa.column("value", sa.String))
    op.bulk_insert(setting, REVIEW_SETTINGS)


def downgrade() -> None:
    """Downgrade schema."""
    keys = ", ".join(f"'{row['key']}'" for row in REVIEW_SETTINGS)
    op.execute(f"DELETE FROM setting WHERE key IN ({keys})")
    op.drop_index("uq_weekly_review_in_progress", table_name="weekly_review")
    op.drop_table("weekly_review")
