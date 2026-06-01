# Operating Model

AI Lab Orchestrator keeps a single point of contact through the front-door API.

The orchestrator only orchestrates. Specialist nodes perform narrow work in the workflow and write structured handoff artifacts.

The harness controls behavior through role files, workflow rules, runtime-control policies, templates, and schemas.

The database tracks project, task, run, handoff, approval, runtime, and event state.

Project artifacts live under `/srv/ai-lab/projects`.

v0.2 project creation creates a PostgreSQL project row, initial task rows for intake, analyst, architect, developer, QA, final report, and runtime inspector, plus the project filesystem.

The default workflow is:

```text
intake -> analyst -> architect -> developer -> qa -> final_report
```

The runtime inspector role exists but does not run by default. It produces an inspection plan based on runtime-control harness policy and does not perform live cron or service edits.

v0.3 uses the configured external Ollama-compatible endpoint for analyst, architect, developer, QA, and final report when available. The orchestrator records the prompt, response, model, provider, timing, status, and fallback metadata in `agent_runs`.

If Ollama is disabled or unreachable, the same workflow completes with deterministic fallback output.

## v0.4 Runtime Inspection

Runtime inspection is invoked explicitly:

```text
POST /projects/{project_id}/runtime-inspect
```

The runtime inspector maps execution paths and validates discover-before-modify readiness. It writes a task packet, agent result, inspection report, evidence JSON, and candidate registry update proposal under the project directory.

Command execution is disabled by default. Operators may set `RUNTIME_INSPECTION_COMMANDS_ENABLED=true`, but commands still run only when the request also sets `allow_read_only_commands=true`. The command runner permits only allowlisted read-only inspection commands and records rejected commands as evidence.

v0.4 approval gates are placeholders only. They indicate that a future modification workflow would require explicit approval after discovery is complete. They do not execute changes.

## v0.5 Controlled Modification Planning

Controlled modification planning is invoked explicitly:

```text
POST /projects/{project_id}/modification-plan
```

The service requires runtime inspection evidence from the project `qa/` folder. If evidence is missing, or if `safe_to_modify=false` and `allow_plan_with_blockers=false`, the response is `blocked` and blocked plan artifacts are still written for auditability.

When planning is allowed, v0.5 writes project-local candidate plan artifacts under `approvals/` and creates a PostgreSQL approval record with status `pending`. The human approval gate is a placeholder only; v0.5 has no approve or execute endpoint.

Approval records are readable through:

```text
GET /projects/{project_id}/approvals
```

## v0.6 Approved Dry-Run Validation

Approval status transitions are invoked explicitly:

```text
POST /projects/{project_id}/approvals/{approval_id}/status
```

Only `pending` or `blocked` approvals can transition. `pending` approvals can become `approved` or `rejected`. `blocked` approvals can become `rejected`, or can become `approved` only when the request explicitly sets `allow_blocked_approval=true`.

Dry-run validation is invoked explicitly:

```text
POST /projects/{project_id}/approvals/{approval_id}/dry-run
```

The service requires approval status `approved`. It loads the approval artifacts, validates the candidate patch structure without applying it, classifies proposed commands without running them, checks rollback plan completeness, writes dry-run validation artifacts under the project `approvals/` folder, and records audit events. v0.6 still has no real execution path.

## v0.7 Sandboxed Plan Validation

Sandbox validation is invoked explicitly:

```text
POST /projects/{project_id}/approvals/{approval_id}/sandbox-run
```

The service requires approval status `approved` and a prior `dry-run-validation-result.json` with status `passed`. It creates a deterministic project-local sandbox under `/srv/ai-lab/projects/<project-id>/sandbox/`, copies approved input artifacts into `sandbox/input/`, applies safe candidate patches only inside `sandbox/workspace/`, writes sandbox logs and manifests, and records audit events.

Command execution is disabled by default with `allow_sandbox_commands=false`. When enabled, only narrow sandbox-local validation commands are allowed. v0.7 still has no production modification or promotion path.
