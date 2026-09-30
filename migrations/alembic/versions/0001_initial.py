"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-30

Creates the canonical schema: users, refresh_tokens, habits, checkins.

Tables are created only if they do not exist yet, so the migration is safe
against a database that was previously initialised by the services'
``create_all`` bootstrap (pre-Alembic deployments).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _exists(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if not _exists("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "email", sa.String(length=255), nullable=False
            ),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column(
                "name", sa.String(length=120), nullable=False, server_default=""
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _exists("refresh_tokens"):
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "revoked", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["user_id"], ["users.id"], ondelete="CASCADE"
            ),
        )
        op.create_index(
            "ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"]
        )
        op.create_index(
            "ix_refresh_tokens_token_hash",
            "refresh_tokens",
            ["token_hash"],
            unique=True,
        )

    if not _exists("habits"):
        op.create_table(
            "habits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column(
                "anchor", sa.String(length=255), nullable=False, server_default=""
            ),
            sa.Column(
                "tiny_behavior",
                sa.String(length=255),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "celebration",
                sa.String(length=255),
                nullable=False,
                server_default="",
            ),
            sa.Column(
                "if_then", sa.String(length=512), nullable=False, server_default=""
            ),
            sa.Column(
                "cue_time", sa.String(length=5), nullable=False, server_default=""
            ),
            sa.Column(
                "active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_habits_user_id", "habits", ["user_id"])

    if not _exists("checkins"):
        op.create_table(
            "checkins",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("habit_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column(
                "completed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column("automaticity", sa.Integer(), nullable=True),
            sa.Column(
                "note", sa.String(length=500), nullable=False, server_default=""
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["habit_id"], ["habits.id"], ondelete="CASCADE"
            ),
            sa.UniqueConstraint("habit_id", "date", name="uq_habit_date"),
        )
        op.create_index("ix_checkins_habit_id", "checkins", ["habit_id"])
        op.create_index("ix_checkins_user_id", "checkins", ["user_id"])


def downgrade() -> None:
    op.drop_table("checkins")
    op.drop_table("habits")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
