# Deployment guide (production)

How to run nexaBoard on a VPS with automatic HTTPS. The local dev workflow
(`docker compose up`) is unchanged — this guide is for the public server.

## Architecture

```
Internet ──► :80/:443  Caddy (auto-HTTPS, Let's Encrypt)
                 ├─ https://example.com      → landing:80  (marketing)
                 └─ https://app.example.com  → frontend:80 (SPA, /api → gateway)
                        internal Docker network only:
                        gateway → users/habits/tracking/insights → postgres
```

- **Only Caddy publishes ports.** Postgres, the gateway and both web apps are
  unreachable from outside (the frontend nginx proxies `/api` itself).
- HTTPS certificates are issued and renewed automatically by Caddy.
- `docker-compose.prod.yml` *extends* the base file — it fails fast with a
  clear message when a required variable is missing.

## Prerequisites

| What | Recommendation |
|---|---|
| Server | Any VPS ≥ 1 vCPU / 1 GB RAM (Hetzner CX22, DigitalOcean, …), Ubuntu 24.04 |
| Domain | One domain + `app.` subdomain (e.g. `example.com` + `app.example.com`) |
| DNS | `A` records: `@`, `www`, `app` → server public IP |

## 1. Server setup (once)

```bash
# Docker (official script)
curl -fsSL https://get.docker.com | sh

# Firewall: only SSH + HTTP/HTTPS
ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

## 2. DNS (once)

Create these records **before** the first start — Let's Encrypt validates
domain ownership at boot:

| Type | Name | Value |
|---|---|---|
| A | `@` | `<server IP>` |
| A | `www` | `<server IP>` |
| A | `app` | `<server IP>` |

Check with `dig +short example.com` from the server.

## 3. App setup (once)

```bash
git clone https://github.com/ibrahimathiongane/google-colab-projects.git /srv/habit-tracker
cd /srv/habit-tracker
```

Create `.env` (gitignored — never commit it):

```bash
cp .env.example .env

# REQUIRED — strong secrets
JWT_SECRET=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 24)

# Your domains
DOMAIN=example.com
APP_HOST=app.example.com
ALLOWED_ORIGINS=https://app.example.com

# Email delivery for password resets (recommended — any SMTP relay;
# STARTTLS on port 587: Resend, Postmark, Brevo, SES...).
# With SMTP_HOST empty the reset link is only written to the service logs.
SMTP_HOST=smtp.postmarkapp.com
SMTP_PORT=587
SMTP_USER=smtp-user
SMTP_PASSWORD=smtp-password
EMAIL_FROM=noreply@yourdomain.com

# Optional: privacy-friendly analytics on the landing (Plausible-compatible,
# no cookies → no consent banner; baked at build time).
# VITE_ANALYTICS_SRC=https://plausible.io/js/script.js
# VITE_ANALYTICS_DOMAIN=yourdomain.com

# Monetisation — Stripe (start with test keys, swap to live keys later)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
# Create the two prices in the Stripe dashboard first (Pro/year subscription,
# Lifetime one-time) and paste their IDs here.
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_LIFETIME=price_...
```

Then register the webhook endpoint in the Stripe dashboard (Developers →
Webhooks → Add endpoint):

- URL: `https://$DOMAIN` is not used by the app — use `https://<your-api-host>/api/billing/webhooks`
  (behind the edge it is the same host as the SPA: `https://$APP_HOST/api/billing/webhooks`)
- Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.paid`
- Copy the signing secret into `STRIPE_WEBHOOK_SECRET`.

Without `STRIPE_SECRET_KEY` the app still runs: checkout/portal answer
`503 Billing is not configured` and everyone stays on the free plan.

Web Push reminders (bell in the dashboard) need a VAPID key pair. Generate
one and paste it into `.env`:

```bash
python scripts/gen-vapid-keys.py   # prints VAPID_PUBLIC_KEY / VAPID_PRIVATE_KEY
```

Without the keys the app still runs: enabling reminders answers
`503 Notifications are not configured`. The `notifications` container runs
the scheduler itself (every 30 s) — no cron needed. Reminders are sent at
each habit's `cue_time` **in the subscribing device's timezone**, only when
the habit is not yet completed that day, and at most once per day.

Start everything:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

First boot takes a few minutes (image builds + certificate issuance).

## 4. Verify

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps   # all healthy
curl -sI https://example.com/health          # 200 (landing)
curl -sI https://app.example.com/            # 200 (app, valid cert)
curl -s https://app.example.com/api/health   # 200 (gateway via SPA proxy)

# SEO artifacts (absolute URLs derived from DOMAIN)
curl -s https://example.com/robots.txt | tail -1   # Sitemap: https://example.com/sitemap.xml
curl -s https://example.com/sitemap.xml | grep loc # https://example.com/
```

Browse both URLs — the browser must show a padlock (Caddy auto-HTTPS).

## 5. Backups (cron)

```bash
crontab -e
# Daily dump at 03:17, keep 14 days, compressed in ./backups/
17 3 * * * cd /srv/habit-tracker && COMPOSE_FLAGS="-f docker-compose.yml -f docker-compose.prod.yml" ./scripts/backup.sh >> /var/log/habit-backups.log 2>&1
```

Restore (interactive, on the server):

```bash
gunzip -c backups/habit-YYYYMMDD-HHMMSS.sql.gz | \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres \
  psql -U habit -d habit_tracker
```

Offsite copy (optional but recommended): rsync the `backups/` folder to
another machine or object storage.

## 6. Day-2 operations

```bash
./scripts/deploy.sh                 # git pull + rebuild + restart + prune
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f gateway
```

- **Schema changes**: push the Alembic revision — `deploy.sh` re-runs the
  migrations service automatically (alembic is idempotent).
- **Landing "Open app" links**: `VITE_APP_URL` is baked at build time from
  `APP_HOST` — if you ever change domains, update `.env` and rebuild
  (`./scripts/deploy.sh` handles it).
- **Certificate issues**: almost always a wrong/missing DNS record — check
  `docker compose ... logs caddy`.

## 7. Security notes

- Secrets (`JWT_SECRET`, `POSTGRES_PASSWORD`) live only in `.env` on the
  server — never in git, never in images.
- All internal HTTP (gateway ↔ services) stays on the Docker network.
- The gateway strips client `X-User-Id` headers; services trust only the
  injected identity (see AGENTS.md).
- Keep the server updated (`apt upgrade`) and the Docker images rebuilt
  (deploy weekly or on push).
