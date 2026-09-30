#!/usr/bin/env bash
# Runs the whole quality suite: ruff + pytest (one process per app) + frontend.
# Usage: PYTHON=/path/to/python ./scripts/test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
FAILED=0

run() {
  echo
  echo "==> $*"
  if ! "$@"; then
    FAILED=1
  fi
}

# --- Backend lint -----------------------------------------------------------
run "$PYTHON" -m ruff check gateway services migrations

# --- Backend tests ----------------------------------------------------------
# One pytest process per app: every service uses the same module names
# (main, models, db, schemas), so a single run would collide.
for app in gateway services/users services/habits services/tracking services/insights; do
  run "$PYTHON" -m pytest "$app/tests" -q
done

# --- Frontend ---------------------------------------------------------------
if [ -d frontend/node_modules ]; then
  run npm --prefix frontend run lint
  run npm --prefix frontend run test
  run npm --prefix frontend run build

  # The PWA artifacts must survive the build.
  for artifact in manifest.json sw.js icon-192.png icon-512.png \
                  icon-maskable-512.png apple-touch-icon.png; do
    if [ ! -f "frontend/dist/$artifact" ]; then
      echo "==> MISSING frontend/dist/$artifact"
      FAILED=1
    fi
  done
else
  echo
  echo "==> frontend skipped (run: npm --prefix frontend ci)"
fi

# --- Landing ------------------------------------------------------------------
if [ -d landing/node_modules ]; then
  run npm --prefix landing run lint
  run npm --prefix landing run test
  run npm --prefix landing run build

  # Marketing assets must survive the build.
  for artifact in images/dashboard.png images/insights.png images/og.png \
                  robots.txt sitemap.xml; do
    if [ ! -f "landing/dist/$artifact" ]; then
      echo "==> MISSING landing/dist/$artifact"
      FAILED=1
    fi
  done

  # The build must have absolutised the social image URL.
  if grep -q "__SITE_URL__" landing/dist/index.html 2>/dev/null; then
    echo "==> landing/dist/index.html still contains __SITE_URL__ tokens"
    FAILED=1
  fi
else
  echo
  echo "==> landing skipped (run: npm --prefix landing ci)"
fi

# --- Production deploy config -------------------------------------------------
# docker-compose.prod.yml must stay renderable (required vars fail fast,
# only Caddy publishes ports) — validated with dummy values.
if command -v docker >/dev/null 2>&1; then
  run env DOMAIN=example.com APP_HOST=app.example.com \
    ALLOWED_ORIGINS=https://app.example.com JWT_SECRET=dummy POSTGRES_PASSWORD=dummy \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml config -q
else
  echo
  echo "==> deploy config skipped (docker not available)"
fi

echo
if [ "$FAILED" -ne 0 ]; then
  echo "FAILURES detected"
  exit 1
fi
echo "All suites passed"
