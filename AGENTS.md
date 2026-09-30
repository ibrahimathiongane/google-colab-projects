# AGENTS.md

## Repository purpose

Science-based habit tracker (microservices). Differentiator: behavioral science approach (Tiny Habits, automaticity, recovery rate) vs. typical streak apps.

## Architecture

- **Gateway** (`gateway/`): FastAPI, JWT auth, reverse proxy to services. Port 8000.
- **Services** (`services/`): each is an independent FastAPI app with its own Dockerfile.
  - `users/` :8001 — auth (access + rotating refresh tokens), password reset, profiles, rate limiting
  - `habits/` :8002 — habit CRUD with scientific fields (anchor, tiny_behavior, celebration, if_then)
  - `tracking/` :8003 — check-ins, streaks, recovery
  - `insights/` :8004 — success rate, habit strength, best time
- **Migrations** (`migrations/`): Alembic, canonical schema (`migrations/models.py`), runs once via the `migrations` compose service.
- **Frontend** (`frontend/`): React + Vite + Recharts. Dev on :5173 (vite), prod behind nginx.
- **Landing** (`landing/`): separate static marketing site (React + Vite, **no API, no gateway**). Dev on :5174, prod behind its own nginx; build context is the repo root because it imports `frontend/src/tokens.css`. "Open app" CTAs point to `VITE_APP_URL` (default `http://localhost:5173`).
- **Edge (prod)**: `docker-compose.prod.yml` + `Caddyfile` — Caddy is the only public entrypoint (80/443, auto-HTTPS): `DOMAIN` → landing, `APP_HOST` → frontend. Postgres/gateway are never published. Full guide: `DEPLOY.md`.
- **DB**: PostgreSQL 16 (shared, each service mirrors the models it needs in its own `models.py`).

## Commands

```bash
cp .env.example .env                # JWT_SECRET is required by compose
docker compose up --build           # start everything (migrations first)
docker compose up -d                # detached
docker compose logs -f <service>    # view logs
docker compose down                 # stop

PYTHON=python3 ./scripts/test.sh    # ruff + pytest per app + eslint + vitest + build + prod config
python -m pytest gateway/tests -q   # a single suite (one pytest process per app)
npm --prefix frontend run test
npm --prefix frontend run lint
npm --prefix landing run dev        # landing dev server on :5174
npm --prefix landing run test

# Production (on the server — see DEPLOY.md)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
./scripts/deploy.sh                 # git pull + rebuild + restart
COMPOSE_FLAGS="-f docker-compose.yml -f docker-compose.prod.yml" ./scripts/backup.sh
```

## Conventions

- The gateway **strips** any client `X-User-Id` and injects it from the JWT only; services trust `X-User-Id` and must still scope every query by it (ownership → 404, never 403).
- Schema changes: edit `migrations/models.py` + write an Alembic revision (`versions/`). Services never call `Base.metadata.create_all` — they open sessions via `Depends(get_db)` and expose `GET /health`.
- JWT secret via `JWT_SECRET` env var (no default in compose; `.env.example` documents it). Refresh tokens are stored hashed and rotated on each refresh.
- Auth routes are rate-limited (sliding window in `services/users/rate_limit.py`); other routes are not.
- Password reset: `POST /users/forgot-password` **always returns 200** (no account enumeration) and stores only the SHA-256 of a single active token (`users.reset_token_hash`, 30 min TTL via `RESET_TTL_MINUTES`); `POST /users/reset-password` consumes the link and revokes every refresh token (logout everywhere). Both are in the gateway `PUBLIC_PATHS`. Email goes over SMTP (`SMTP_*` env in `services/users/mailer.py`) — with no `SMTP_HOST` the reset link is logged instead, so dev/tests never need credentials; links point at `{APP_URL}/reset-password`. Mail copy is English-only for now.
- Frontend calls `/api/{service}/{path}` (vite dev proxy → gateway, nginx in prod) and auto-refreshes an expired access token once (`frontend/src/api.js`).
- Check-in upsert: one per `(habit_id, date)` — re-checking toggles completion. Dates are `YYYY-MM-DD` in the *user's* timezone (`localDate()`).
- Lint: `ruff.toml` at the root pins the Python rule set; ESLint flat config lives in `frontend/eslint.config.js`.
- Tests must run in **separate pytest processes** (services share module names `main`, `models`, `db`, `schemas`) — `scripts/test.sh` does this for you.
- PWA: `frontend/public/` holds `manifest.json`, `sw.js` and the generated icons (from `icon.svg` / `icon-maskable.svg` via `rsvg-convert`). The SW is registered **only in production** (`frontend/src/pwa.js`); bump `VERSION` in `sw.js` when the cache strategy changes. nginx serves `sw.js`/`manifest.json` with `no-cache` — every location that declares an `add_header` must `include /etc/nginx/security-headers.conf` (nginx does not inherit headers otherwise).
- i18n: i18next, dictionaries in `frontend/src/i18n/{en,fr}.json` — **every new user-facing string goes into both files** (a test fails otherwise). Components use `useTranslation()`; backend error strings are mapped in `frontend/src/i18n/apiErrors.js` (unknown messages pass through). Language lives in `localStorage.lang` and drives `<html lang>`/`document.title`.
- Design: Linear-inspired dark-first tokens in `frontend/src/tokens.css`, rules in `frontend/DESIGN.md` — **no hardcoded hex in components** (charts: CSS sets the fill from a token; the JSX value is only a static fallback). Buttons default to ghost; `--primary` is the single accent (CTA/focus/brand), semantic colors are status-only. Inter Variable is self-hosted (`@fontsource-variable/inter`), mono only for metadata, titles use negative tracking, sentence case everywhere.
- Landing: never call `/api` (no proxy in `landing/nginx.conf`); it imports the app's tokens via `../../frontend/src/tokens.css` (so its Docker build uses the repo root as context). `landing/public/images/*.png` are **real app screenshots** — regenerate them from the app when the UI changes.
