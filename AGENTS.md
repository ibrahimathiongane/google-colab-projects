# AGENTS.md

## Repository purpose

Science-based habit tracker (microservices). Differentiator: behavioral science approach (Tiny Habits, automaticity, recovery rate) vs. typical streak apps.

## Architecture

- **Gateway** (`gateway/`): FastAPI, JWT auth, reverse proxy to services. Port 8000.
- **Services** (`services/`): each is an independent FastAPI app with its own Dockerfile.
  - `users/` :8001 — auth (access + rotating refresh tokens), profiles, rate limiting
  - `habits/` :8002 — habit CRUD with scientific fields (anchor, tiny_behavior, celebration, if_then)
  - `tracking/` :8003 — check-ins, streaks, recovery
  - `insights/` :8004 — success rate, habit strength, best time
- **Migrations** (`migrations/`): Alembic, canonical schema (`migrations/models.py`), runs once via the `migrations` compose service.
- **Frontend** (`frontend/`): React + Vite + Recharts. Dev on :5173 (vite), prod behind nginx.
- **DB**: PostgreSQL 16 (shared, each service mirrors the models it needs in its own `models.py`).

## Commands

```bash
cp .env.example .env                # JWT_SECRET is required by compose
docker compose up --build           # start everything (migrations first)
docker compose up -d                # detached
docker compose logs -f <service>    # view logs
docker compose down                 # stop

PYTHON=python3 ./scripts/test.sh    # ruff + pytest per app + eslint + vitest + build
python -m pytest gateway/tests -q   # a single suite (one pytest process per app)
npm --prefix frontend run test
npm --prefix frontend run lint
```

## Conventions

- The gateway **strips** any client `X-User-Id` and injects it from the JWT only; services trust `X-User-Id` and must still scope every query by it (ownership → 404, never 403).
- Schema changes: edit `migrations/models.py` + write an Alembic revision (`versions/`). Services never call `Base.metadata.create_all` — they open sessions via `Depends(get_db)` and expose `GET /health`.
- JWT secret via `JWT_SECRET` env var (no default in compose; `.env.example` documents it). Refresh tokens are stored hashed and rotated on each refresh.
- Auth routes are rate-limited (sliding window in `services/users/rate_limit.py`); other routes are not.
- Frontend calls `/api/{service}/{path}` (vite dev proxy → gateway, nginx in prod) and auto-refreshes an expired access token once (`frontend/src/api.js`).
- Check-in upsert: one per `(habit_id, date)` — re-checking toggles completion. Dates are `YYYY-MM-DD` in the *user's* timezone (`localDate()`).
- Lint: `ruff.toml` at the root pins the Python rule set; ESLint flat config lives in `frontend/eslint.config.js`.
- Tests must run in **separate pytest processes** (services share module names `main`, `models`, `db`, `schemas`) — `scripts/test.sh` does this for you.
