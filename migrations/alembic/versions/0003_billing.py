"""billing tables (Stripe customers + subscriptions)

Revision ID: 0003_billing
Revises: 0002_password_reset
Create Date: 2026-09-30

Creates billing_customers and billing_subscriptions. Only created if they
do not exist yet (same safety as 0001).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_billing"
down_revision: str | None = "0002_password_reset"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _exists(name: str) -> bool:
    bind = op.get_bind()
    return sa.inspect(bind).has_table(name)


def upgrade() -> None:
    if not _exists("billing_customers"):
        op.create_table(
            "billing_customers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("stripe_customer_id", sa.String(64), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, server_default=""),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_billing_customers_user_id", "billing_customers", ["user_id"],
            unique=True,
        )
        op.create_index(
            "ix_billing_customers_stripe_customer_id",
            "billing_customers",
            ["stripe_customer_id"],
            unique=True,
        )

    if not _exists("billing_subscriptions"):
        op.create_table(
            "billing_subscriptions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("stripe_subscription_id", sa.String(64), nullable=True),
            sa.Column("plan", sa.String(16), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("price_id", sa.String(64), nullable=False, server_default=""),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "cancel_at_period_end",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_billing_subscriptions_user_id",
            "billing_subscriptions",
            ["user_id"],
            unique=True,
        )
        op.create_index(
            "ix_billing_subscriptions_stripe_subscription_id",
            "billing_subscriptions",
            ["stripe_subscription_id"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_table("billing_subscriptions")
    op.drop_table("billing_customers")
