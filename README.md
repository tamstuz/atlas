# AI Lab Orchestrator

AI Lab Orchestrator is a repo-based installer that turns a fresh Ubuntu Server 24.04 minimal VM into an AI Lab control plane.

v0.1 provides a simple foundation:

- FastAPI front-door API
- LangGraph workflow scaffold
- PostgreSQL for project, task, run, approval, and event state
- Qdrant for future semantic memory
- production and candidate harness directories
- production and candidate skill directories
- runtime registries
- project workspace creation
- systemd service files
- health, doctor, backup, and project creation scripts
- optional external Ollama-compatible LLM endpoint

Ollama is not installed by this repo and may run on another server.

## Architecture Summary

```text
User -> Front Door API -> LangGraph -> Specialist Nodes -> Harness/DB/Filesystem
```

The orchestrator receives requests, creates project state, routes placeholder workflow nodes, and stores durable operational records. Harness and skill files live on the filesystem so future changes can be proposed under candidate directories before promotion.

## Fresh Install Quickstart

On Ubuntu Server 24.04:

```bash
git clone https://github.com/tamstuz/atlas.git ai-lab-orchestrator
cd ai-lab-orchestrator
sudo ./install.sh
```

The runtime root is always:

```text
/srv/ai-lab
```

The installer creates `.env` from `.env.example` if it does not already exist.

## Healthcheck

```bash
cd /srv/ai-lab
scripts/healthcheck.sh
scripts/doctor.sh
```

The API health endpoint returns:

```json
{
  "status": "ok",
  "service": "ai-lab-orchestrator"
}
```

## First Project Creation Test

```bash
cd /srv/ai-lab
scripts/create-project.sh "test project" "Create a hello world Python script"
```

This creates a project folder under:

```text
/srv/ai-lab/projects/<project-id>/
```

with `project-state.json`, `task-board.json`, `decision-log.md`, `workspace/`, `handoffs/`, `qa/`, and `final/`.

## External Ollama Configuration

Set the external endpoint in `.env`:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama.example.local:11434
DEFAULT_MODEL=gemma4:26b
```

If `OLLAMA_ENABLED=false`, LLM calls are skipped. If the endpoint is unreachable, app startup still succeeds and LLM call functions return a clear error.

## Known Limitations

- v0.1 has no web UI.
- v0.1 has no authentication system.
- v0.1 does not implement autonomous self-improvement.
- v0.1 does not implement production skill or harness promotion automation.
- The worker runner service is a placeholder.
- The LangGraph nodes contain placeholder logic only.
