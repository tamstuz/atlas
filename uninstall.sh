#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "uninstall.sh must run as root or with sudo."
  exit 1
fi

systemctl stop ai-lab-worker-runner.service 2>/dev/null || true
systemctl stop ai-lab-orchestrator.service 2>/dev/null || true
systemctl disable ai-lab-worker-runner.service 2>/dev/null || true
systemctl disable ai-lab-orchestrator.service 2>/dev/null || true
rm -f /etc/systemd/system/ai-lab-worker-runner.service /etc/systemd/system/ai-lab-orchestrator.service
systemctl daemon-reload

if [[ -d "${AI_LAB_ROOT}" ]]; then
  cd "${AI_LAB_ROOT}"
  docker compose --env-file .env down 2>/dev/null || true
fi

read -r -p "Delete ${AI_LAB_ROOT}? Type DELETE to remove data, anything else preserves it: " answer
if [[ "${answer}" == "DELETE" ]]; then
  rm -rf "${AI_LAB_ROOT}"
  echo "Deleted ${AI_LAB_ROOT}."
else
  echo "Preserved ${AI_LAB_ROOT}."
fi
