#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_LAB_ROOT="${AI_LAB_ROOT:-/srv/ai-lab}"
AI_LAB_USER="${AI_LAB_USER:-ai-lab}"
AI_LAB_GROUP="${AI_LAB_GROUP:-ai-lab}"
UBUNTU_CODENAME=""

docker_compose_available() {
  command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1
}

install_docker_from_official_repo() {
  if [[ -z "${UBUNTU_CODENAME}" ]]; then
    echo "Unable to determine Ubuntu codename for Docker apt repository."
    exit 1
  fi

  echo "Installing Docker from the official Docker apt repository..."
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc

  cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable
EOF

  apt-get update
  apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin
}

ensure_docker_compose() {
  if docker_compose_available; then
    echo "Docker and Docker Compose plugin are already available."
    docker --version
    docker compose version
    return
  fi

  install_docker_from_official_repo

  if ! docker_compose_available; then
    echo "Docker Compose plugin is still unavailable after Docker installation."
    echo "Expected 'docker compose version' to work. Check Docker apt repository setup and package installation logs."
    exit 1
  fi

  docker --version
  docker compose version
}

if [[ "${EUID}" -ne 0 ]]; then
  echo "install.sh must run as root or with sudo."
  exit 1
fi

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  UBUNTU_CODENAME="${VERSION_CODENAME:-}"
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    echo "Warning: Ubuntu Server 24.04 LTS is the supported target. Detected ${PRETTY_NAME:-unknown}."
  fi
fi

echo "Installing required packages..."
apt-get update
apt-get install -y curl git ca-certificates python3 python3-venv python3-pip
ensure_docker_compose

if ! getent group "${AI_LAB_GROUP}" >/dev/null; then
  groupadd --system "${AI_LAB_GROUP}"
fi

if ! id "${AI_LAB_USER}" >/dev/null 2>&1; then
  useradd --system --gid "${AI_LAB_GROUP}" --home-dir "${AI_LAB_ROOT}" --shell /usr/sbin/nologin "${AI_LAB_USER}"
fi

mkdir -p "${AI_LAB_ROOT}"
tar -C "${REPO_DIR}" --exclude ".git" --exclude ".venv" -cf - . | tar -C "${AI_LAB_ROOT}" -xf -

cd "${AI_LAB_ROOT}"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

python3 -m venv orchestrator/.venv
orchestrator/.venv/bin/pip install --upgrade pip
orchestrator/.venv/bin/pip install -r orchestrator/requirements.txt

mkdir -p projects runtime/logs runtime/registries
chown -R "${AI_LAB_USER}:${AI_LAB_GROUP}" "${AI_LAB_ROOT}"

docker compose --env-file .env up -d postgres qdrant
"${AI_LAB_ROOT}/scripts/init-db.sh"

install -m 0644 systemd/ai-lab-orchestrator.service /etc/systemd/system/ai-lab-orchestrator.service
install -m 0644 systemd/ai-lab-worker-runner.service /etc/systemd/system/ai-lab-worker-runner.service
systemctl daemon-reload
systemctl enable ai-lab-orchestrator.service ai-lab-worker-runner.service
systemctl restart ai-lab-orchestrator.service
systemctl restart ai-lab-worker-runner.service

"${AI_LAB_ROOT}/scripts/healthcheck.sh" || true

cat <<'NEXT'

AI Lab Orchestrator v0.1 install complete.

Next commands:
  cd /srv/ai-lab
  scripts/doctor.sh
  scripts/healthcheck.sh
  scripts/create-project.sh "test project" "Create a hello world Python script"

NEXT
