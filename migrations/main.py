"""HTTP wrapper around Alembic for deployments without a boot hook.

docker-compose runs `alembic upgrade head` as a one-shot job before the
services start. On Vercel there is no such hook, so the gateway forwards
`POST /api/migrations/upgrade` here. The route stays out of the public
surface (gateway PUBLIC_PATHS entry) and requires a shared token — the
operation itself is idempotent, `upgrade head` is a no-op once applied.
"""
import os
import pathlib

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, Header, HTTPException

BASE = pathlib.Path(__file__).resolve().parent

app = FastAPI(title="migrations")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Sync on purpose: FastAPI runs sync handlers in a threadpool, so the
# (short) Alembic run doesn't block the event loop.
@app.post("/upgrade")
def upgrade(x_migrate_token: str | None = Header(default=None)) -> dict[str, str]:
    expected = os.environ.get("MIGRATE_TOKEN", "")
    if not expected or x_migrate_token != expected:
        raise HTTPException(status_code=401, detail="Invalid migrate token")
    cfg = Config(str(BASE / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE / "alembic"))
    command.upgrade(cfg, "head")
    return {"status": "upgraded"}
