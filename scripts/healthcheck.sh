#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
ENV_FILE="${AI_LAB_ROOT}/.env"
DOCKER_CMD=()

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

wait_for_health() {
  local url="$1"
  local attempts="${2:-30}"
  local delay="${3:-2}"

  for attempt in $(seq 1 "${attempts}"); do
    if curl -fsS "${url}" >/dev/null; then
      return 0
    fi
    echo "Waiting for ${url} (${attempt}/${attempts})..."
    sleep "${delay}"
  done

  echo "Health endpoint did not become ready: ${url}"
  return 1
}

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

HOST="${AI_LAB_HOST:-127.0.0.1}"
if [[ "${HOST}" == "0.0.0.0" ]]; then
  HOST="127.0.0.1"
fi
PORT="${AI_LAB_PORT:-8088}"

echo "Checking FastAPI /health..."
wait_for_health "http://${HOST}:${PORT}/health"

echo "Checking Docker Compose services..."
cd "${AI_LAB_ROOT}"
resolve_docker_cmd
"${DOCKER_CMD[@]}" compose --env-file .env ps postgres qdrant

echo "Checking PostgreSQL container..."
"${DOCKER_CMD[@]}" compose --env-file .env ps postgres | grep -qi "running"

echo "Checking Qdrant container..."
"${DOCKER_CMD[@]}" compose --env-file .env ps qdrant | grep -qi "running"

echo "Healthcheck passed."
