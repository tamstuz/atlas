# Install

AI Lab Orchestrator v0.1 targets Ubuntu Server 24.04 LTS minimal installs.

```bash
git clone <repo-url> ai-lab-orchestrator
cd ai-lab-orchestrator
sudo ./install.sh
```

The installer:

1. checks permissions
2. warns when the OS is not Ubuntu 24.04
3. installs required packages
4. creates the `ai-lab` user and group
5. copies repo files to `/srv/ai-lab`
6. creates a Python virtual environment
7. installs Python dependencies
8. creates `.env` from `.env.example` if missing
9. starts PostgreSQL and Qdrant with Docker Compose
10. initializes the database
11. installs systemd units
12. starts services
13. runs the healthcheck

Review `/srv/ai-lab/.env` after install, especially external LLM settings.
