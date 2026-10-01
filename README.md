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

┌────────────┐  fully separate: static, no API, no gateway
│  Landing   │──▶ "Open app" CTAs → VITE_APP_URL (the frontend)
│ React/Vite │
│ :5174      │
└────────────┘
```

## Quick start

```bash
cp .env.example .env     # set JWT_SECRET (required by docker-compose)
docker compose up --build
```

- Frontend: http://localhost:5173
- Landing: http://localhost:5174
- API Gateway: http://localhost:8000
- Health: `GET /health` on the gateway and on every service

## Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy is the only public entrypoint (80/443) and issues HTTPS certificates
automatically: `DOMAIN` → landing, `APP_HOST` → the app (Postgres and the
gateway stay on the internal network). Full guide — server setup, DNS,
backups, day-2 operations: **[DEPLOY.md](DEPLOY.md)**.

The landing ships SEO artifacts (Open Graph/Twitter card, canonical,
`robots.txt`, `sitemap.xml` — absolute URLs built from `DOMAIN`) and
optional privacy-friendly analytics (`VITE_ANALYTICS_SRC`, Plausible-compatible).

## Vercel (services)

One Vercel project deploys the whole stack via `vercel.json`
([services docs](https://vercel.com/docs/services), beta):

- **Routing**: `/api/(.*)` → `gateway` (the only public backend — it receives the
  full `/api/<service>/<path>` and proxies with the JWT rules), everything else →
  `frontend`. `landing` and all backends stay internal; the landing gets its own
  host-based rewrite as soon as a second hostname is attached (same split as the
  Caddy deploy).
- **Bindings**: the gateway is the only service that calls its siblings; the
  bindings inject the `*_URL` variables it already reads. Bindings resolve at
  runtime only — never at build time.
- **Build-time env**: the FastAPI modules read `JWT_SECRET` and `DATABASE_URL` at
  import → both must be marked *Available during build*. Leave `VITE_API_URL`
  unset so the SPA keeps calling same-origin `/api`.
- **Runtime env**: `ALLOWED_ORIGINS`, `APP_URL`, `MIGRATE_TOKEN`, `VAPID_*`,
  `STRIPE_*`, `SMTP_*` (see `.env.example`).
- **Database**: Vercel ships none — attach a managed Postgres (e.g. the Neon
  integration from the marketplace) and set `DATABASE_URL`.
- **Migrations**: no boot hook on Vercel; after each schema deploy run
  `POST /api/migrations/upgrade` with header `X-Migrate-Token: $MIGRATE_TOKEN`
  (idempotent — compose still runs Alembic as a one-shot job locally).
- **Reminders**: the cue-time loop only ticks inside warm function instances
  (best-effort; a cold instance sends nothing). A guaranteed window needs a
  dedicated worker or Vercel Cron on a paid plan.
- Local: `vercel dev` runs every service and injects the bindings.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| gateway | 8000 | JWT auth, request routing |
| users | 8001 | Register, login, profiles, refresh tokens |
| habits | 8002 | CRUD habits with scientific fields |
| tracking | 8003 | Check-ins, streaks, recovery |
| insights | 8004 | Success rate, habit strength, best time |
| billing | 8005 | Stripe checkout, customer portal, entitlements |
| notifications | 8006 | Web-push reminders (VAPID, cue-time scheduler) |
| migrations | — | Alembic schema bootstrap (runs once) |
| frontend | 5173 | React SPA served by nginx (proxies `/api` → gateway) |
| landing | 5174 | Static marketing site (no API, no gateway) |

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
| GET | `/api/billing/` | Current plan (free / pro / lifetime) |
| POST | `/api/billing/checkout` | Stripe Checkout session (`{"plan": "pro" \| "lifetime"}`) |
| POST | `/api/billing/portal` | Stripe customer portal session |
| POST | `/api/billing/webhooks` | Stripe events (public, signature-verified) |
| GET | `/api/notifications/` | Is this device subscribed to reminders? |
| GET | `/api/notifications/vapid-public-key` | VAPID key for `PushManager.subscribe` |
| POST | `/api/notifications/subscribe` | Save this device (endpoint, keys, tz, lang) |
| POST | `/api/notifications/unsubscribe` | Remove this device |

## Security notes (Phase 0)

- Gateway strips any client-supplied `X-User-Id` and injects it from the JWT only.
- Refresh tokens are stored hashed, rotated on every refresh, revoked on logout.
- Login/register are rate-limited (sliding window per email and per IP).
- Password reset links are single-use (hashed at rest, 30 min TTL, same 200 answer for unknown accounts) and changing the password revokes every session; email goes through SMTP (`SMTP_*` env, link logged when unset).
- Containers run as a non-root user; images are pinned.
- Monetisation: Stripe Checkout runs on Stripe's hosted pages (no card data touches the app); webhooks are signature-verified and never call the Stripe API back. The free plan is limited to one habit — creations beyond that return `402`, edits/deletes stay open.

## Phase 1 features

### PWA

- Installable on iOS/Android/desktop: `frontend/public/manifest.json` +
  icons (192/512/maskable/apple-touch).
- Service worker (`frontend/public/sw.js`): app-shell precache, network-first
  navigations with offline fallback, cache-first for hashed assets.
  **`/api/*` is never cached.**
- Registered only in production builds (`frontend/src/pwa.js`); `sw.js` and
  `manifest.json` are served with `Cache-Control: no-cache` by nginx.

### Reminders (web push)

- Opt-in bell on the dashboard (the permission prompt only ever appears on a
  click); the subscription stores the device's timezone offset and language.
- The `notifications` service sends a push at each habit's `cue_time`
  (device-local), only when it isn't completed yet — at most one per habit
  per device per day — and drops endpoints the push service reports as gone.
- VAPID keys via `python scripts/gen-vapid-keys.py` (see `.env.example`);
  without them, enabling reminders answers `503`.

### i18n (EN + FR)

- i18next dictionaries in `frontend/src/i18n/{en,fr}.json` — a test enforces
  that both locales stay key-for-key identical.
- Language switcher in the nav, persisted in `localStorage.lang`, applied to
  `<html lang>` and `document.title`.
- Backend error messages are mapped to localized strings
  (`frontend/src/i18n/apiErrors.js`); unknown messages pass through as-is.
- Dates are formatted with the active locale (`en-US` / `fr-FR`).

### Mobile (Android, Capacitor)

The app also ships as an Android app: a Capacitor 8 shell
(`frontend/capacitor.config.json`, project in `frontend/android/`, id
`com.habittracker.app`) that loads a **local bundle** of the same frontend.

- The WebView has its own origin, so the API origin is baked at build time:
  `VITE_API_URL=https://app.example.com npm --prefix frontend run build:mobile`
  (no trailing slash). Without it the build keeps same-origin `/api` (web
  default) and every call would 404 inside the shell.
- The shell never registers the service worker and the reminders bell shows
  "unsupported": WebView push doesn't deliver (native APNs/FCM is out of
  Phase 1) — see `frontend/src/native.js`.
- Local API testing: add the shell origin (`http://localhost`) to
  `ALLOWED_ORIGINS` and bridge the gateway to the device with
  `adb reverse tcp:8000 tcp:8000` (works on emulator and USB device), then
  build with `VITE_API_URL=http://localhost:8000`. Cleartext HTTP is only
  permitted to loopback hosts
  (`frontend/android/app/src/main/res/xml/network_security_config.xml`);
  a public API must be HTTPS.
- Debug APK: `npm --prefix frontend run build:mobile`, then
  `cd frontend/android && ./gradlew assembleDebug` →
  `app/build/outputs/apk/debug/app-debug.apk`. Needs the Android SDK
  (`ANDROID_HOME` + `local.properties`) and **JDK 17–24** — Gradle 8.14
  won't run on newer JDKs; Android Studio is optional.
- iOS: needs a Mac — run `npx cap add ios` there, same config.

## Design system (Linear-inspired)

Dark-first, achromatic canvas + one accent (`#5e6ad2`), shared by the app
**and** the landing page. **Reference: `frontend/DESIGN.md`.**

- **Tokens** in `frontend/src/tokens.css`: canvas/surfaces, hairlines, ink
  opacity scale, primary accent, indicator colors (success/danger/warning),
  type, 4px spacing grid, 2/6/12 radii, motion curves. Never hardcode a hex
  value in a component.
- **Type**: self-hosted Inter Variable (`@fontsource-variable/inter`, no
  CDN), negative tracking on titles, mono (`--font-mono`) for metadata only
  (metrics, badges, dates).
- **Buttons** default to a quiet ghost — the primary CTA (`--primary`) is
  used once per view. Semantic colors appear only as status signals.
- Verified headless (Chromium): no horizontal overflow at 375px, computed
  canvas `#08090a`, CTA `#5e6ad2`, Inter loaded, negative tracking.

## Tests

```bash
# everything (ruff + pytest per service + eslint + vitest + build)
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
PYTHON=.venv/bin/python ./scripts/test.sh
```

Backend, frontend and landing suites can be run separately:

```bash
pip install -r requirements-dev.txt
python -m ruff check gateway services migrations
python -m pytest gateway/tests -q          # one pytest process per app:
python -m pytest services/users/tests -q   # services share module names

npm --prefix frontend ci
npm --prefix frontend run lint
npm --prefix frontend run test

npm --prefix landing ci
npm --prefix landing run lint
npm --prefix landing run test
```
