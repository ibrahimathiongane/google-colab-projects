"""Thin, testable wrapper around the Stripe SDK.

Every network call of the billing service goes through this module so the
tests can monkeypatch it (no Stripe account needed to run the suite).
Keys are test keys until the operator swaps them in production.
"""
import os

import stripe


class ConfigurationError(RuntimeError):
    """A required Stripe env var is missing."""


def _configure() -> None:
    key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
    if not key:
        raise ConfigurationError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = key


def create_checkout_session(
    *,
    customer: str | None,
    price: str,
    mode: str,
    plan: str,
    user_id: int,
    success_url: str,
    cancel_url: str,
) -> str:
    """Return the URL of a hosted Stripe Checkout session.

    ``metadata`` carries the attribution (user + plan) so the webhook can
    persist everything without calling the Stripe API back.
    """
    _configure()
    params: dict = {
        "mode": mode,
        "line_items": [{"price": price, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(user_id),
        "metadata": {"user_id": str(user_id), "plan": plan},
    }
    if customer:
        params["customer"] = customer
    if mode == "subscription":
        params["subscription_data"] = {
            "metadata": {"user_id": str(user_id), "plan": plan}
        }
    session = stripe.checkout.Session.create(**params)
    return session.url


def create_portal_session(*, customer: str, return_url: str) -> str:
    """Return the URL of the Stripe Customer Portal (cancel/update card)."""
    _configure()
    session = stripe.billing_portal.Session.create(
        customer=customer, return_url=return_url
    )
    return session.url
