# Habit Tracker — Science-Based

A microservices habit tracker built on behavioral science (BJ Fogg's Tiny Habits, implementation intentions, automaticity tracking). Different from market apps: focuses on **recovery rate** over streak-shame, **habit strength index**, and **tiny anchored behaviors** instead of rigid daily goals.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────────────────────────────┐
│ Frontend  │────▶│ Gateway  │────▶│  Microservices (FastAPI)         │
│ React/Vite│     │ :8000    │     │  users :8001  habits :8002       │
└──────────┘     └──────────┘     │  tracking :8003  insights :8004  │
                                  └──────────────────────────────────┘
                                            │
                                       ┌────▼────┐
                                       │ Postgres │
                                       └─────────┘
```

## Quick start

```bash
docker compose up --build
```

- Frontend: http://localhost:5173
- API Gateway: http://localhost:8000

## Services

| Service | Port | Purpose |
|---------|------|---------|
| gateway | 8000 | JWT auth, request routing |
| users | 8001 | Register, login, profiles |
| habits | 8002 | CRUD habits with scientific fields |
| tracking | 8003 | Check-ins, streaks, recovery |
| insights | 8004 | Success rate, habit strength, best time |

## Scientific model

- **Tiny Habits** (BJ Fogg): anchor → tiny behavior → celebration
- **Implementation intentions**: auto-generated if-then plans
- **Automaticity**: self-reported 1-10 "how automatic did this feel"
- **Habit strength**: `0.6 × consistency + 0.4 × automaticity`
- **Recovery rate**: days to return after a miss (anti-streak-shame)

## API

All routes prefixed with `/api`. Auth via `Authorization: Bearer <token>`.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/users/register` | Create account |
| POST | `/api/users/login` | Get JWT |
| GET | `/api/habits/` | List habits |
| POST | `/api/habits/` | Create habit |
| DELETE | `/api/habits/{id}` | Deactivate habit |
| POST | `/api/tracking/checkin` | Record check-in |
| GET | `/api/tracking/today?date=YYYY-MM-DD` | Today's check-ins |
| GET | `/api/tracking/streaks` | Current streaks |
| GET | `/api/insights/summary` | Scientific insights |
