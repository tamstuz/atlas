# Architecture

```text
User -> Front Door API -> LangGraph -> Specialist Nodes -> Harness/DB/Filesystem
```

The FastAPI service is the front door. It exposes health, safe configuration, project creation, project read, workflow run, and LLM status endpoints.
v0.4 adds `POST /projects/{project_id}/runtime-inspect` for read-only runtime inspection.
v0.5 adds `POST /projects/{project_id}/modification-plan` and `GET /projects/{project_id}/approvals` for approval-gated planning.
v0.6 adds `POST /projects/{project_id}/approvals/{approval_id}/status` for human approval transitions and `POST /projects/{project_id}/approvals/{approval_id}/dry-run` for approved dry-run validation.
v0.7 adds `POST /projects/{project_id}/approvals/{approval_id}/sandbox-run` for project-local sandbox validation after approval and passing dry-run validation.
v0.8 adds `POST /projects/{project_id}/approvals/{approval_id}/change-package` for human-reviewed production change package generation after approval, passed dry-run validation, and passed sandbox validation. It also adds `GET /projects/{project_id}/change-packages` for package records.

LangGraph is the workflow layer. v0.2 runs intake, analyst, architect, developer, QA, and final report. The stable LangGraph `thread_id` is the project id.

v0.3 keeps the same workflow and adds optional LLM-backed execution for analyst, architect, developer, QA, and final report. Each eligible node assembles a prompt from the active role harness files, task packet, project request, and agent result schema. If the external Ollama-compatible endpoint is disabled or unavailable, the workflow uses deterministic fallback output.

PostgreSQL stores durable project, task, run, handoff, approval, skill, harness, runtime asset, and event records.

v0.2 persists workflow state snapshots to PostgreSQL `events`. This is a minimal checkpoint fallback, not a formal LangGraph PostgreSQL checkpoint saver.

Qdrant is included for future semantic memory.

Filesystem and Git hold harness files, skills, project artifacts, reports, and runtime registries.

Each workflow node loads only its role file and required shared rules from `HARNESS_DIR`, then writes a task packet YAML and agent result JSON under the project `handoffs/` directory. The final report is written to `final/final-report.md`.

LLM prompts, responses, model names, provider, timing, status, errors, and fallback metadata are stored in `agent_runs` JSONB fields.

The runtime inspector is a separate project action, not part of the default specialist workflow. It loads runtime-inspector harness policy, creates a runtime-inspector task packet, maps execution-path evidence, validates discover-before-modify requirements, and writes project-local artifacts under `handoffs/` and `qa/`.

Runtime inspection command execution is disabled by default with `RUNTIME_INSPECTION_COMMANDS_ENABLED=false`. When enabled and requested, the shell inspection service enforces an allowlist of read-only commands and records skipped, rejected, completed, or failed command evidence. v0.4 does not mutate global runtime registries; it writes candidate registry update proposals only under the project `qa/` directory.

The modification planning service reads the project-local runtime inspection evidence before generating any candidate plan. It writes approval artifacts under the project `approvals/` directory, creates an approval record in PostgreSQL, records events, and records a deterministic `modification_planner` agent run. It never executes commands, applies patches, mutates `harness/prod`, or mutates global runtime registries.

The approval transition service moves approval records from `pending` or `blocked` to `approved` or `rejected`, records audit events, and does not execute anything. Blocked approvals can only become approved when the request explicitly sets `allow_blocked_approval=true`.

The dry-run validation service requires an approved approval record. It reads the project-local modification plan and `dry-run.patch`, validates patch targets, classifies proposed commands without running them, checks rollback plan completeness, writes validation artifacts under the project `approvals/` directory, updates approval validation metadata, and records audit events. It does not apply patches, edit cron, edit systemd, restart services, use sudo, mutate `harness/prod`, or mutate global runtime registries.

The sandbox service requires an approved approval record and a passed dry-run validation result. It creates `/srv/ai-lab/projects/<project-id>/sandbox/`, copies approved artifacts into `sandbox/input/`, applies safe candidate patches only under `sandbox/workspace/`, validates sandbox command plans, records command logs and file manifests, writes sandbox reports, and records events. It never mounts or mutates production paths, global runtime registries, or `harness/prod`.

The change package service requires an approved approval record, a passed dry-run validation result, and a passed sandbox validation result. It writes package artifacts under `/srv/ai-lab/projects/<project-id>/change-package/`, copies source artifacts into `change-package/source/`, classifies exact commands for human review only, creates a final `production_change_package` approval record with status `pending`, and records package events. It does not call shell execution services, apply production patches, edit cron, edit systemd, restart services, use sudo, mutate global runtime registries, or mutate `harness/prod`.
