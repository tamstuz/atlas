#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
cd "${AI_LAB_ROOT}"

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

if docker compose --env-file .env ps postgres | grep -qi "running"; then
  docker compose --env-file .env exec -T postgres psql \
    -U "${POSTGRES_USER:-ailab}" \
    -d "${POSTGRES_DB:-ailab}" \
    -f /docker-entrypoint-initdb.d/001-init.sql
else
  echo "PostgreSQL container is not running; skipping DB initialization."
fi
