# Habit Tracker — Science-Based

A microservices habit tracker built on behavioral science (BJ Fogg's Tiny Habits, implementation intentions, automaticity tracking). Different from market apps: focuses on **recovery rate** over streak-shame, **habit strength index**, and **tiny anchored behaviors** instead of rigid daily goals.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────────────────────────────┐
│ Frontend  │────▶│ Gateway  │────▶│  Microservices (FastAPI)         │
│ React/Vite│     │ :8000    │     │  users :8001  habits :8002       │
│ via nginx │     └──────────┘     │  tracking :8003  insights :8004  │
└──────────┘                      └──────────────────────────────────┘
                                            │
                                       ┌────▼────┐   ┌────────────┐
                                       │ Postgres │◀──│ migrations │
                                       └─────────┘   │ (Alembic)  │
                                                     └────────────┘
```

## Quick start

```bash
cp .env.example .env     # set JWT_SECRET (required by docker-compose)
docker compose up --build
```

- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000
- Health: `GET /health` on the gateway and on every service

## Services

| Service | Port | Purpose |
|---------|------|---------|
| gateway | 8000 | JWT auth, request routing |
| users | 8001 | Register, login, profiles, refresh tokens |
| habits | 8002 | CRUD habits with scientific fields |
| tracking | 8003 | Check-ins, streaks, recovery |
| insights | 8004 | Success rate, habit strength, best time |
| migrations | — | Alembic schema bootstrap (runs once) |
| frontend | 5173 | React SPA served by nginx (proxies `/api` → gateway) |

## Scientific model

- **Tiny Habits** (BJ Fogg): anchor → tiny behavior → celebration
- **Implementation intentions**: auto-generated if-then plans
- **Automaticity**: self-reported 1-10 "how automatic did this feel"
- **Habit strength**: `0.6 × consistency + 0.4 × automaticity`
- **Recovery rate**: days to return after a miss (anti-streak-shame)
- **Grace day**: a streak survives until the day ends, not the calendar flip

## API

All routes prefixed with `/api`. Auth via `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/users/register` | Create account (returns access + refresh token) |
| POST | `/api/users/login` | Get JWT pair |
| POST | `/api/users/refresh` | Rotate the refresh token |
| POST | `/api/users/logout` | Revoke the refresh token |
| GET | `/api/users/me` | Current profile |
| GET | `/api/habits/` | List habits |
| POST | `/api/habits/` | Create habit |
| PUT | `/api/habits/{id}` | Partial update (regenerates the if-then) |
| DELETE | `/api/habits/{id}` | Deactivate habit |
| POST | `/api/tracking/checkin` | Record check-in (upsert per day) |
| GET | `/api/tracking/today?date=YYYY-MM-DD` | Today's check-ins |
| GET | `/api/tracking/range?habit_id=&days=` | History for charts |
| GET | `/api/tracking/streaks` | Current streaks |
| GET | `/api/insights/summary?tz_offset=` | Scientific insights |

## Security notes (Phase 0)

- Gateway strips any client-supplied `X-User-Id` and injects it from the JWT only.
- Refresh tokens are stored hashed, rotated on every refresh, revoked on logout.
- Login/register are rate-limited (sliding window per email and per IP).
- Containers run as a non-root user; images are pinned.

## Tests

```bash
# everything (ruff + pytest per service + eslint + vitest + build)
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
PYTHON=.venv/bin/python ./scripts/test.sh
```

Backend and frontend suites can be run separately:

```bash
pip install -r requirements-dev.txt
python -m ruff check gateway services migrations
python -m pytest gateway/tests -q          # one pytest process per app:
python -m pytest services/users/tests -q   # services share module names

npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run test
```
