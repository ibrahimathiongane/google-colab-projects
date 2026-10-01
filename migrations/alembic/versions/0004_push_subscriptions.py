"""push subscriptions + reminder logs

Revision ID: 0004_push_subscriptions
Revises: 0003_billing
Create Date: 2026-10-01

Creates push_subscriptions (one row per device that opted into web push)
and reminder_logs (one push per device/habit/local day). Only created if
they do not exist yet (same safety as 0001).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_push_subscriptions"
down_revision: str | None = "0003_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _exists(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if not _exists("push_subscriptions"):
        op.create_table(
            "push_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("endpoint", sa.String(512), nullable=False),
            sa.Column("p256dh", sa.String(128), nullable=False),
            sa.Column("auth", sa.String(64), nullable=False),
            sa.Column("tz_offset", sa.Integer(), nullable=False),
            sa.Column(
                "lang", sa.String(5), nullable=False, server_default="en"
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_push_subscriptions_user_id",
            "push_subscriptions",
            ["user_id"],
        )
        op.create_index(
            "ix_push_subscriptions_endpoint",
            "push_subscriptions",
            ["endpoint"],
            unique=True,
        )

    if not _exists("reminder_logs"):
        op.create_table(
            "reminder_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("subscription_id", sa.Integer(), nullable=False),
            sa.Column("habit_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint(
                "subscription_id",
                "habit_id",
                "date",
                name="uq_reminder_day",
            ),
        )
        op.create_index(
            "ix_reminder_logs_subscription_id",
            "reminder_logs",
            ["subscription_id"],
        )
        op.create_index(
            "ix_reminder_logs_habit_id", "reminder_logs", ["habit_id"]
        )


def downgrade() -> None:
    op.drop_table("reminder_logs")
    op.drop_table("push_subscriptions")
