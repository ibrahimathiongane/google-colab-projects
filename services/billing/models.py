from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class BillingCustomer(Base):
    """Mirror of the shared billing_customers table (Stripe customer map)."""

    __tablename__ = "billing_customers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    stripe_customer_id = Column(String(64), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, default="")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BillingSubscription(Base):
    """Mirror of billing_subscriptions: the current plan of a user.

    No row (or a non-entitled status) = free plan.
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
