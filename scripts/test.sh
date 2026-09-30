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

echo
if [ "$FAILED" -ne 0 ]; then
  echo "FAILURES detected"
  exit 1
fi
echo "All suites passed"
