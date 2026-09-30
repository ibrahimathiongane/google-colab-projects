"""Transactional email over SMTP (stdlib only).

Configuration (env vars):
    SMTP_HOST      — unset/empty ⇒ emails are logged instead of sent, so
                     local development and tests never need credentials
    SMTP_PORT      — default 587 (STARTTLS)
    SMTP_USER      — login, optional (unauthenticated relays exist)
    SMTP_PASSWORD  — password for SMTP_USER
    EMAIL_FROM     — From header, default "noreply@localhost"

Works with any provider exposing SMTP: Resend, Postmark, Brevo, SES, ...
The mail body is English-only for now (see AGENTS.md).
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("users.mail")

RESET_SUBJECT = "Reset your Habit Tracker password"


def build_reset_email(to: str, reset_url: str, ttl_minutes: int) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = os.environ.get("EMAIL_FROM", "noreply@localhost")
    msg["To"] = to
    msg["Subject"] = RESET_SUBJECT
    msg.set_content(
        "Hi,\n\n"
        "Someone asked to reset the password of your Habit Tracker account.\n"
        f"This link can be used once and expires in {ttl_minutes} minutes:\n\n"
        f"  {reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email.\n"
    )
    return msg


def send_reset_email(to: str, reset_url: str, ttl_minutes: int = 30) -> None:
    """Send the reset link. Raises on SMTP failure (callers must catch)."""
    host = os.environ.get("SMTP_HOST", "").strip()
    if not host:
        # No relay configured: surface the link in the logs so the flow can
        # be exercised end-to-end without any credentials.
        logger.warning(
            "SMTP not configured — reset link for %s: %s", to, reset_url
        )
        return

    msg = build_reset_email(to, reset_url, ttl_minutes)
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)
    logger.info("reset email sent to %s", to)
