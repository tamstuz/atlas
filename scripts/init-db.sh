#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
DOCKER_CMD=()
cd "${AI_LAB_ROOT}"

resolve_docker_cmd() {
  if command -v docker >/dev/null 2>&1 && docker ps >/dev/null 2>&1; then
    DOCKER_CMD=(docker)
    return
  fi

  if command -v sudo >/dev/null 2>&1 && sudo -n docker ps >/dev/null 2>&1; then
    DOCKER_CMD=(sudo -n docker)
    return
  fi

  echo "Docker is not available to this user. Join the docker group and re-login, or run with sudo."
  exit 1
}

wait_for_postgres() {
  local attempts="${1:-60}"
  local delay="${2:-2}"

  for attempt in $(seq 1 "${attempts}"); do
    if "${DOCKER_CMD[@]}" compose --env-file .env exec -T postgres pg_isready \
      -U "${POSTGRES_USER:-ailab}" \
      -d "${POSTGRES_DB:-ailab}" >/dev/null 2>&1; then
      return 0
    fi
    echo "Waiting for PostgreSQL readiness (${attempt}/${attempts})..."
    sleep "${delay}"
  done

  echo "PostgreSQL did not become ready after ${attempts} attempts."
  return 1
}

if [[ -f .env ]]; then
  set -a
  . ./.env
  set +a
fi

resolve_docker_cmd
wait_for_postgres

"${DOCKER_CMD[@]}" compose --env-file .env exec -T postgres psql \
  -U "${POSTGRES_USER:-ailab}" \
  -d "${POSTGRES_DB:-ailab}" \
  -f /docker-entrypoint-initdb.d/001-init.sql
