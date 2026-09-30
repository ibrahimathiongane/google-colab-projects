#!/usr/bin/env bash
# Pull the latest main and restart the production stack.
# Run it on the server from the repo root (see DEPLOY.md).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> git pull"
git pull --ff-only

echo "==> build"
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

echo "==> up (migrations re-run here, alembic is idempotent)"
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --remove-orphans

echo "==> prune dangling images"
docker image prune -f

echo "==> status"
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
