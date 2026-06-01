# AI Lab Orchestrator

AI Lab Orchestrator is a repo-based installer that turns a fresh Ubuntu Server 24.04 minimal VM into an AI Lab control plane.

v0.8 provides a basic working orchestrator:

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
- approval-gated controlled modification planning
- project-local candidate modification plan artifacts
- approval status transitions for pending or blocked approval records
- approved dry-run validation for candidate plans and patches
- deterministic patch, command plan, and rollback plan validation without execution
- project-local sandbox run endpoint for approved, dry-run-passed plans
- sandbox artifacts, command logs, and file manifests under each project
- production change package generation after approved dry-run and sandbox validation
- human execution, rollback, pre-flight, and post-change checklists
- exact command plan documents for human review only
- final human approval records for package review only

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

## Controlled Modification Planning

v0.5 adds approval-gated planning only:

```bash
curl -X POST http://localhost:8088/projects/<project-id>/modification-plan \
  -H "Content-Type: application/json" \
  -d '{"change_request":"Update the service command","target_type":"systemd","target_hint":"example.service","allow_plan_with_blockers":false}'
```

If runtime inspection evidence is missing or incomplete, the response is blocked and explains the blockers. If planning is allowed, the plan remains pending human approval. v0.5 never executes the plan.

Planning artifacts are written under:

- `/srv/ai-lab/projects/<project-id>/approvals/modification-plan.md`
- `/srv/ai-lab/projects/<project-id>/approvals/modification-plan.json`
- `/srv/ai-lab/projects/<project-id>/approvals/dry-run.patch`
- `/srv/ai-lab/projects/<project-id>/approvals/approval-request.json`

Blocked requests write:

- `/srv/ai-lab/projects/<project-id>/approvals/blocked-modification-plan.md`
- `/srv/ai-lab/projects/<project-id>/approvals/blocked-modification-plan.json`

Read approval records:

```bash
curl http://localhost:8088/projects/<project-id>/approvals
```

## Approved Dry-Run Validation

v0.6 adds approval status transitions and dry-run validation only:

```bash
curl -X POST http://localhost:8088/projects/<project-id>/approvals/<approval-id>/status \
  -H "Content-Type: application/json" \
  -d '{"status":"approved","reason":"Reviewed by human.","allow_blocked_approval":false}'

curl -X POST http://localhost:8088/projects/<project-id>/approvals/<approval-id>/dry-run \
  -H "Content-Type: application/json" \
  -d '{"validation_mode":"full_dry_run"}'
```

Dry-run validation writes:

- `/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-report.md`
- `/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-result.json`
- `/srv/ai-lab/projects/<project-id>/approvals/patch-validation.json`

The validator reads the candidate plan and `dry-run.patch`, classifies proposed commands, checks rollback plan completeness, records events, and never applies patches or runs modifying commands.

## Sandboxed Plan Validation

v0.7 adds project-local sandbox validation after approval and passing dry-run validation:

```bash
curl -X POST http://localhost:8088/projects/<project-id>/approvals/<approval-id>/sandbox-run \
  -H "Content-Type: application/json" \
  -d '{"sandbox_mode":"full_sandbox","allow_sandbox_commands":false}'
```

Sandbox artifacts are written under:

- `/srv/ai-lab/projects/<project-id>/sandbox/sandbox-run-report.md`
- `/srv/ai-lab/projects/<project-id>/sandbox/sandbox-run-result.json`
- `/srv/ai-lab/projects/<project-id>/sandbox/sandbox-command-log.json`
- `/srv/ai-lab/projects/<project-id>/sandbox/sandbox-file-manifest.json`
- `/srv/ai-lab/projects/<project-id>/sandbox/applied.patch`

The sandbox copies approved inputs into `sandbox/input/`, applies safe candidate patches only inside `sandbox/workspace/`, and blocks production mutation paths. Sandbox command execution is disabled by default; when explicitly enabled, only narrow validation commands can run with the sandbox as the working directory.

## Production Change Package

v0.8 adds production change packaging after approval, passed dry-run validation, and passed sandbox validation:

```bash
curl -X POST http://localhost:8088/projects/<project-id>/approvals/<approval-id>/change-package \
  -H "Content-Type: application/json" \
  -d '{"change_window":"Sunday 01:00 UTC","operator":"ops","notes":"review only"}'

curl http://localhost:8088/projects/<project-id>/change-packages
```

Change package artifacts are written under:

- `/srv/ai-lab/projects/<project-id>/change-package/production-change-package.md`
- `/srv/ai-lab/projects/<project-id>/change-package/production-change-package.json`
- `/srv/ai-lab/projects/<project-id>/change-package/human-execution-checklist.md`
- `/srv/ai-lab/projects/<project-id>/change-package/exact-command-plan.md`
- `/srv/ai-lab/projects/<project-id>/change-package/rollback-checklist.md`
- `/srv/ai-lab/projects/<project-id>/change-package/preflight-checklist.md`
- `/srv/ai-lab/projects/<project-id>/change-package/postchange-checklist.md`
- `/srv/ai-lab/projects/<project-id>/change-package/final-approval-request.json`
- `/srv/ai-lab/projects/<project-id>/change-package/source-artifact-manifest.json`

Source artifacts are copied into `change-package/source/` when present. The exact command plan is marked human-only, dangerous commands are classified as `blocked_for_agent`, and no command execution service is called. v0.8 creates a final `production_change_package` approval record with status `pending`; this is review of the package only, not execution approval.

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

- v0.8 has no web UI.
- v0.8 has no authentication system.
- v0.8 does not implement autonomous self-improvement.
- v0.8 does not implement production skill or harness promotion automation.
- v0.8 does not implement production command execution.
- The worker runner service is a placeholder.
- Specialist output is deterministic placeholder content when no external LLM is available.
- LLM prompts and responses are stored in `agent_runs` JSONB input/output fields.
- Runtime inspector creates read-only inspection artifacts only; it does not edit cron or services.
- Modification planning, dry-run validation, sandbox validation, and change packaging do not apply production patches, edit cron, edit systemd, restart services, use sudo, mutate global registries, or mutate `harness/prod`.
