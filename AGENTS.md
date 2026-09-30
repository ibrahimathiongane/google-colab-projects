# AGENTS.md

## Repository purpose

Science-based habit tracker (microservices). Differentiator: behavioral science approach (Tiny Habits, automaticity, recovery rate) vs. typical streak apps.

## Architecture

- **Gateway** (`gateway/`): FastAPI, JWT auth, reverse proxy to services. Port 8000.
- **Services** (`services/`): each is an independent FastAPI app with its own Dockerfile.
  - `users/` :8001 — auth, profiles
  - `habits/` :8002 — habit CRUD with scientific fields (anchor, tiny_behavior, celebration, if_then)
  - `tracking/` :8003 — check-ins, streaks, recovery
  - `insights/` :8004 — success rate, habit strength, best time
- **Frontend** (`frontend/`): React + Vite + Recharts. Port 5173.
- **DB**: PostgreSQL 16 (shared, each service has its own models.py)

## Commands

```bash
docker compose up --build          # start everything
docker compose up -d               # detached
docker compose logs -f <service>   # view logs
docker compose down                # stop
```

## Conventions

- Services read user identity from `X-User-Id` header (set by gateway after JWT decode).
- Each service runs `Base.metadata.create_all` on startup — no migrations.
- JWT secret via `JWT_SECRET` env var (default: `dev-secret-change-me`).
- Frontend proxies `/api` → `gateway:8000` via vite config.
- Check-in upsert: one per `(habit_id, date)` — re-checking toggles completion.
