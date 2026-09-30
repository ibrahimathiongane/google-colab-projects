"""password reset columns on users

Revision ID: 0002_password_reset
Revises: 0001_initial
Create Date: 2026-09-30

Adds the single-active reset token columns to `users`. Both are nullable,
so the migration is a safe in-place ALTER (no backfill, no downtime).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_password_reset"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "reset_token_hash" not in existing:
        op.add_column(
            "users", sa.Column("reset_token_hash", sa.String(64), nullable=True)
        )
        op.create_unique_constraint(
            "uq_users_reset_token_hash", "users", ["reset_token_hash"]
        )
    if "reset_expires_at" not in existing:
        op.add_column(
            "users",
            sa.Column("reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = {c["name"] for c in sa.inspect(bind).get_columns("users")}
    if "reset_expires_at" in existing:
        op.drop_column("users", "reset_expires_at")
    if "reset_token_hash" in existing:
        op.drop_constraint("uq_users_reset_token_hash", "users", type_="unique")
        op.drop_column("users", "reset_token_hash")
