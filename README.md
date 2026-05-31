# AI Lab Orchestrator

AI Lab Orchestrator is a repo-based installer that turns a fresh Ubuntu Server 24.04 minimal VM into an AI Lab control plane.

v0.4 provides a basic working orchestrator:

- FastAPI front-door API
- LangGraph workflow scaffold
- PostgreSQL-backed project, task, run, handoff, and event state
- Qdrant for future semantic memory
- production and candidate harness directories
- production and candidate skill directories
- runtime registries
- project workspace creation
- deterministic workflow run: intake -> analyst -> architect -> developer -> QA -> final report
- harness role loading per workflow node
- optional LLM-backed specialist execution through an external Ollama-compatible endpoint
- structured task packets and agent result files
- final report generation
- `/llm/status` external Ollama status endpoint
- systemd service files
- health, doctor, backup, and project creation scripts
- optional external Ollama-compatible LLM endpoint
- read-only runtime inspection endpoint
- execution-path mapping artifacts
- discover-before-modify validation
- candidate runtime registry update files only

Ollama is not installed by this repo and may run on another server.

## Architecture Summary

```text
User -> Front Door API -> LangGraph -> Specialist Nodes -> Harness/DB/Filesystem
```

The orchestrator receives requests, creates DB-backed project and task state, routes workflow nodes, loads the active harness role files, writes handoff artifacts, and stores durable operational records. Harness and skill files live on the filesystem so future changes can be proposed under candidate directories before promotion.

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

## Run the Workflow

```bash
curl -X POST http://localhost:8088/projects/<project-id>/run
curl http://localhost:8088/projects/<project-id>
```

The run writes:

- `/srv/ai-lab/projects/<project-id>/handoffs/<step>-<role>-task-packet.yaml`
- `/srv/ai-lab/projects/<project-id>/handoffs/<step>-<role>-agent-result.json`
- `/srv/ai-lab/projects/<project-id>/final/final-report.md`

LangGraph uses `thread_id = project_id`. Workflow state snapshots are persisted to PostgreSQL `events`.

## Runtime Inspection

v0.4 adds read-only runtime inspection:

```bash
curl -X POST http://localhost:8088/projects/<project-id>/runtime-inspect \
  -H "Content-Type: application/json" \
  -d '{"target_type":"unknown","target_hint":"","allow_read_only_commands":false}'
```

The runtime inspector writes:

- `/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-task-packet.yaml`
- `/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-agent-result.json`
- `/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-report.md`
- `/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-evidence.json`
- `/srv/ai-lab/projects/<project-id>/qa/candidate-runtime-registry-updates.yaml`

Command execution is disabled by default:

```env
RUNTIME_INSPECTION_COMMANDS_ENABLED=false
```

Even when enabled, v0.4 only permits allowlisted read-only inspection commands. It does not modify files, cron, services, `harness/prod`, or global runtime registries.

## External Ollama Configuration

Set the external endpoint in `.env`:

```env
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://ollama.example.local:11434
LLM_TIMEOUT_SECONDS=120
DEFAULT_MODEL=gemma4:26b
ANALYST_MODEL=
ARCHITECT_MODEL=
DEVELOPER_MODEL=
QA_MODEL=
FINAL_REPORT_MODEL=
```

If `OLLAMA_ENABLED=false`, LLM calls are skipped. If the endpoint is unreachable, app startup and project workflows still succeed using deterministic fallback output.

When Ollama is enabled and reachable, analyst, architect, developer, QA, and final report nodes call the configured model. Empty per-role model values fall back to `DEFAULT_MODEL`.

Check status:

```bash
curl http://localhost:8088/llm/status
```

## Known Limitations

- v0.4 has no web UI.
- v0.4 has no authentication system.
- v0.4 does not implement autonomous self-improvement.
- v0.4 does not implement production skill or harness promotion automation.
- The worker runner service is a placeholder.
- Specialist output is deterministic placeholder content when no external LLM is available.
- LLM prompts and responses are stored in `agent_runs` JSONB input/output fields.
- Runtime inspector creates read-only inspection artifacts only; it does not edit cron or services.
