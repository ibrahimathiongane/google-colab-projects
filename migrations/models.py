"""Canonical database schema.

Single source of truth for the shared PostgreSQL database. Services keep
mirrored ORM models (read/write views of these tables) but never create
schema themselves: `alembic upgrade head` runs in the `migrations`
container before any service starts.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(120), nullable=False, default="")
    # Password reset: only the SHA-256 of the token is stored (like refresh
    # tokens); NULL = no pending reset.
    reset_token_hash = Column(String(64), nullable=True, unique=True, index=True)
    reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="refresh_tokens")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    anchor = Column(String(255), nullable=False, default="")
    tiny_behavior = Column(String(255), nullable=False, default="")
    celebration = Column(String(255), nullable=False, default="")
    if_then = Column(String(512), nullable=False, default="")
    cue_time = Column(String(5), nullable=False, default="")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = (
        UniqueConstraint("habit_id", "date", name="uq_habit_date"),
    )

    id = Column(Integer, primary_key=True)
    habit_id = Column(
        Integer,
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(Date, nullable=False)
    completed = Column(Boolean, nullable=False, default=True)
    automaticity = Column(Integer)  # 1-10 self-report (SRHI-inspired)
    note = Column(String(500), nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingCustomer(Base):
    """Stripe customer mapping — one row per user (first checkout wins,
    refreshed when Stripe issues a new customer)."""

    __tablename__ = "billing_customers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingSubscription(Base):
    """Current plan of a user. A row exists only after the first payment:
    no row (or a canceled one) = free plan. ``plan`` is 'pro' (recurring)
    or 'lifetime' (one-time payment — no stripe subscription id)."""

    __tablename__ = "billing_subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    stripe_subscription_id = Column(
        String(64), nullable=True, unique=True, index=True
    )
    plan = Column(String(16), nullable=False)
    status = Column(String(32), nullable=False, default="active")
    price_id = Column(String(64), nullable=False, default="")
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
