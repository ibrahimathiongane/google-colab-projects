from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


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


class BillingSubscription(Base):
    """Read-only mirror of billing_subscriptions (shared Postgres).

    Used locally to enforce the free-plan habit limit without a network
    hop: ownership of billing data stays in the billing service — we only
    read the plan here.
    """

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
