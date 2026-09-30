#!/usr/bin/env bash
# PostgreSQL backup with retention (default: keep 14 days).
#
# Cron (see DEPLOY.md):
#   17 3 * * * cd /srv/habit-tracker && COMPOSE_FLAGS="-f docker-compose.yml -f docker-compose.prod.yml" ./scripts/backup.sh >> /var/log/habit-backups.log 2>&1
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

BACKUP_DIR="${BACKUP_DIR:-backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
# Space-separated compose -f flags; empty = the dev stack.
COMPOSE_FLAGS="${COMPOSE_FLAGS:-}"

mkdir -p "$BACKUP_DIR"
FILE="$BACKUP_DIR/habit-$(date +%Y%m%d-%H%M%S).sql.gz"

# shellcheck disable=SC2086  # COMPOSE_FLAGS is intentionally word-split
docker compose $COMPOSE_FLAGS exec -T postgres \
  sh -c 'pg_dump -U "${POSTGRES_USER:-habit}" "${POSTGRES_DB:-habit_tracker}"' \
  | gzip > "$FILE"

# Never keep an empty/failed dump.
if [ ! -s "$FILE" ]; then
  rm -f "$FILE"
  echo "backup FAILED (empty dump)" >&2
  exit 1
fi

echo "backup ok: $FILE ($(du -h "$FILE" | cut -f1))"
find "$BACKUP_DIR" -name "habit-*.sql.gz" -mtime "+$KEEP_DAYS" -delete
