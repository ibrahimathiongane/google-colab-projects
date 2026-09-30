import hashlib
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
import mailer
import models
import rate_limit
import schemas
from db import engine, get_db
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("users")

ACCESS_TTL = timedelta(minutes=15)
REFRESH_TTL = timedelta(days=30)
RESET_TTL = timedelta(
    minutes=int(os.environ.get("RESET_TTL_MINUTES", "30"))
)
# Public base URL of the SPA — where reset links point back to.
APP_URL = os.environ.get("APP_URL", "http://localhost:5173").rstrip("/")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is owned by the `migrations` service (Alembic), not by us.
    yield
    engine.dispose()


app = FastAPI(title="Users Service", lifespan=lifespan)


def hashpw(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_tokens(db: Session, user_id: int) -> dict:
    """Create an access JWT plus a rotating refresh token."""
    now = datetime.now(UTC)
    access = jwt.encode(
        {
            "sub": str(user_id),
            "typ": "access",
            "iat": now,
            "exp": now + ACCESS_TTL,
        },
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    raw_refresh = secrets.token_urlsafe(48)
    db.add(
        models.RefreshToken(
            user_id=user_id,
            token_hash=_hash_token(raw_refresh),
            expires_at=now + REFRESH_TTL,
        )
    )
    db.commit()
    return {"token": access, "refresh_token": raw_refresh}


def _user_out(user: models.User) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name}


def require_user_id(x_user_id: str | None = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(401, "Authentication required")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(401, "Invalid user identity") from None


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(503, "database unavailable") from None
    return {"status": "ok"}


@app.post("/register")
def register(
    body: schemas.RegisterIn,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit.allow(f"register-ip:{ip}", limit=10):
        raise HTTPException(429, "Too many attempts, try again later")

    email = body.email.lower()
    if db.query(models.User).filter_by(email=email).first():
        # Do not reveal whether the address exists: same answer as a
        # successful registration keeps account enumeration neutral.
        raise HTTPException(400, "This email cannot be used")

    user = models.User(
        email=email,
        password_hash=hashpw(body.password),
        name=body.name.strip(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    tokens = issue_tokens(db, user.id)
    logger.info("user registered id=%s", user.id)
    return {**tokens, "user": _user_out(user)}


@app.post("/login")
def login(
    body: schemas.LoginIn,
    request: Request,
    db: Session = Depends(get_db),
):
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    if not rate_limit.allow(f"login:{email}") or not rate_limit.allow(
        f"login-ip:{ip}", limit=50
    ):
        raise HTTPException(429, "Too many attempts, try again later")

    user = db.query(models.User).filter_by(email=email).first()
    if not user or not verify(body.password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    tokens = issue_tokens(db, user.id)
    logger.info("user login id=%s", user.id)
    return {**tokens, "user": _user_out(user)}


def _as_utc(value: datetime) -> datetime:
    """Naive datetimes from the driver are interpreted as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@app.post("/refresh")
def refresh(body: schemas.RefreshIn, db: Session = Depends(get_db)):
    row = (
        db.query(models.RefreshToken)
        .filter_by(token_hash=_hash_token(body.refresh_token))
        .first()
    )
    now = datetime.now(UTC)
    if (
        row is None
        or row.revoked
        or _as_utc(row.expires_at) <= now
        or row.user is None
    ):
        raise HTTPException(401, "Invalid refresh token")

    # Rotation: the presented token is consumed and a new one issued.
    row.revoked = True
    db.commit()
    tokens = issue_tokens(db, row.user_id)
    return {**tokens, "user": _user_out(row.user)}


@app.post("/logout")
def logout(body: schemas.RefreshIn, db: Session = Depends(get_db)):
    row = (
        db.query(models.RefreshToken)
        .filter_by(token_hash=_hash_token(body.refresh_token))
        .first()
    )
    if row is not None and not row.revoked:
        row.revoked = True
        db.commit()
    return {"ok": True}


@app.get("/me")
def me(
    user_id: int = Depends(require_user_id),
    db: Session = Depends(get_db),
):
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return _user_out(user)


@app.post("/forgot-password")
def forgot_password(
    body: schemas.ForgotPasswordIn,
    request: Request,
    db: Session = Depends(get_db),
):
    """Start a password reset. Always answers 200: whether the account
    exists is never revealed (same reasoning as register)."""
    email = body.email.lower()
    ip = request.client.host if request.client else "unknown"
    if not rate_limit.allow(f"forgot:{email}", limit=3) or not rate_limit.allow(
        f"forgot-ip:{ip}", limit=10
    ):
        raise HTTPException(429, "Too many attempts, try again later")

    user = db.query(models.User).filter_by(email=email).first()
    if user is not None:
        # Single active token per account: requesting again invalidates the
        # previous link. Only its hash is stored.
        raw = secrets.token_urlsafe(32)
        user.reset_token_hash = _hash_token(raw)
        user.reset_expires_at = datetime.now(UTC) + RESET_TTL
        db.commit()
        reset_url = f"{APP_URL}/reset-password?token={raw}"
        try:
            mailer.send_reset_email(
                user.email, reset_url, ttl_minutes=int(RESET_TTL.total_seconds() // 60)
            )
        except Exception:
            # Mailer trouble stays server-side: the answer must be identical
            # for existing and unknown accounts.
            logger.exception("reset email failed for user id=%s", user.id)
    return {"ok": True}


@app.post("/reset-password")
def reset_password(
    body: schemas.ResetPasswordIn,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not rate_limit.allow(f"reset-ip:{ip}", limit=10):
        raise HTTPException(429, "Too many attempts, try again later")

    user = (
        db.query(models.User)
        .filter_by(reset_token_hash=_hash_token(body.token))
        .first()
    )
    now = datetime.now(UTC)
    if (
        user is None
        or user.reset_expires_at is None
        or _as_utc(user.reset_expires_at) <= now
    ):
        raise HTTPException(400, "Invalid or expired reset link")

    user.password_hash = hashpw(body.password)
    user.reset_token_hash = None  # token consumed: cannot be reused
    user.reset_expires_at = None
    # Changing the password logs every device out.
    (
        db.query(models.RefreshToken)
        .filter_by(user_id=user.id, revoked=False)
        .update({"revoked": True})
    )
    db.commit()
    logger.info("password reset for user id=%s", user.id)
    return {"ok": True}
