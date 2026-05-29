#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
ENV_FILE="${AI_LAB_ROOT}/.env"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  . "${ENV_FILE}"
  set +a
fi

echo "OS:"
cat /etc/os-release | grep -E "PRETTY_NAME|VERSION_ID" || true
echo
echo "Docker:"
docker --version || true
docker compose version || true
echo
echo "Python:"
python3 --version || true
echo
echo "AI Lab root: ${AI_LAB_ROOT}"
echo "LLM endpoint: ${OLLAMA_BASE_URL:-not configured}"
echo
echo "systemd:"
systemctl --no-pager --lines=0 status ai-lab-orchestrator.service || true
systemctl --no-pager --lines=0 status ai-lab-worker-runner.service || true
echo
echo "Containers:"
cd "${AI_LAB_ROOT}" 2>/dev/null && docker compose --env-file .env ps || true
