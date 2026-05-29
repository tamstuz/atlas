#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-test project}"
REQUEST="${2:-Create a hello world Python script}"
AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"

if [[ -f "${AI_LAB_ROOT}/.env" ]]; then
  set -a
  . "${AI_LAB_ROOT}/.env"
  set +a
fi

HOST="${AI_LAB_HOST:-127.0.0.1}"
if [[ "${HOST}" == "0.0.0.0" ]]; then
  HOST="127.0.0.1"
fi

curl -fsS \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"${NAME}\",\"request\":\"${REQUEST}\"}" \
  "http://${HOST}:${AI_LAB_PORT:-8088}/projects"
echo
