#!/usr/bin/env bash
set -euo pipefail

AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
BACKUP_DIR="${BACKUP_DIR:-${AI_LAB_ROOT}/runtime/backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${BACKUP_DIR}/ai-lab-backup-${STAMP}.tar.gz"

mkdir -p "${BACKUP_DIR}"
echo "Warning: .env may contain secrets and is included when present."

tar -czf "${ARCHIVE}" -C "${AI_LAB_ROOT}" \
  harness skills runtime/registries projects .env 2>/dev/null || true

echo "Backup written to ${ARCHIVE}"
