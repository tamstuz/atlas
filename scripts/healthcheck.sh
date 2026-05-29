#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
ENV_FILE="${AI_LAB_ROOT}/.env"

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
curl -fsS "http://${HOST}:${PORT}/health" >/dev/null

echo "Checking Docker Compose services..."
cd "${AI_LAB_ROOT}"
docker compose --env-file .env ps postgres qdrant

echo "Checking PostgreSQL container..."
docker compose --env-file .env ps postgres | grep -qi "running"

echo "Checking Qdrant container..."
docker compose --env-file .env ps qdrant | grep -qi "running"

echo "Healthcheck passed."
