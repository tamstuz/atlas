# AI Lab Orchestrator - v0.4 Build Directive

## Purpose

Build v0.4 as a read-only runtime inspector and controlled execution planning release.

v0.4 targets the original reliability failure this project exists to prevent: agents must not create, edit, or replace files without first proving the real runtime execution path. The runtime inspector must help map cron jobs, systemd services, scripts, Docker services, Python entrypoints, logs, config files, working directories, and verification commands before any future modification workflow is considered.

This release is inspection and planning only.

## Scope

Implement only:

1. A project runtime-inspection endpoint.
2. Runtime-inspector task execution.
3. Execution-path inspection planning.
4. Discover-before-modify enforcement for cron, service, and runtime work.
5. Runtime-inspection artifacts under the project workspace.
6. Runtime-inspector DB task/run/event records.
7. Read-only shell inspection command support, disabled by default.
8. Blocking of all modify commands.
9. Approval gate placeholders for future modification workflows.
10. Validation docs and tests.

Do not add unrelated features.

## Hard Limits

Do not implement:

1. Live file modification.
2. Live cron editing.
3. Live systemd editing.
4. Service restart.
5. Sudo-capable agents.
6. Root-capable autonomous behavior.
7. Package installation by agents.
8. Self-improvement.
9. Skill or harness promotion.
10. Production harness mutation.
11. Web UI.
12. Arbitrary shell execution.
13. Network scanning.
14. Approval-based modification execution.

Approval gates in v0.4 are placeholders only. They may report that approval would be required in a future release, but they must not execute approved changes.

## Required Endpoint

Add:

```text
POST /projects/{project_id}/runtime-inspect
```

Optional request body:

```json
{
  "target_type": "cron|systemd|script|docker|python|unknown",
  "target_hint": "",
  "allow_read_only_commands": false
}
```

Defaults:

1. `target_type`: `unknown`
2. `target_hint`: empty string
3. `allow_read_only_commands`: `false`

Even when `allow_read_only_commands` is true, command execution must remain disabled unless the environment explicitly enables it.

Required response shape:

```json
{
  "project_id": "",
  "status": "complete",
  "runtime_inspection_report_path": "",
  "task_packet_path": "",
  "agent_result_path": "",
  "inspection_summary": "",
  "blockers": [],
  "evidence": [],
  "safe_to_modify": false
}
```

In v0.4, `safe_to_modify` must default to `false`. Returning `true` is allowed only when all discover-before-modify requirements are satisfied, and even then v0.4 must not modify anything.

## Required Implementation Areas

Add or update:

```text
orchestrator/app/nodes/runtime_inspector.py
orchestrator/app/services/runtime_inspection_service.py
orchestrator/app/services/discovery_validator.py
orchestrator/app/services/shell_inspection_service.py
```

The runtime inspector must:

1. Load the project from PostgreSQL.
2. Load the project filesystem state.
3. Load runtime-inspector harness policy.
4. Create or update the `runtime_inspector` task.
5. Generate a runtime-inspector task packet.
6. Generate an execution-path inspection plan.
7. Optionally run allowlisted read-only commands.
8. Collect structured evidence.
9. Validate discover-before-modify completeness.
10. Write runtime-inspection artifacts.
11. Write DB task, run, event, and handoff records where supported.
12. Return structured JSON.

## Required Harness Files

The runtime inspector must load:

```text
harness/prod/roles/runtime-inspector.md
harness/prod/runtime-control/discover-before-modify.md
harness/prod/runtime-control/absolute-path-policy.md
harness/prod/runtime-control/cron-debug-policy.md
harness/prod/runtime-control/service-debug-policy.md
harness/prod/workflow-rules/handoff-policy.md
harness/prod/workflow-rules/completion-gates.md
```

Do not mutate `harness/prod`.

If clarification is needed, place candidate policy changes under a candidate path only. Do not promote or apply them in v0.4.

## Discover-Before-Modify Validator

Create a reusable validator that checks whether the inspection identified:

1. Scheduler/source.
2. Exact command.
3. Runtime working directory.
4. Absolute script path.
5. Config files.
6. Log files.
7. Verification command.
8. Owner/service context.
9. Current observed behavior.
10. Proposed next step.

Return:

```json
{
  "safe_to_modify": false,
  "missing_requirements": [],
  "satisfied_requirements": [],
  "confidence": "low|medium|high",
  "reason": ""
}
```

This validator is a reporting and gating mechanism only. It must not execute modifications.

## Read-Only Shell Inspection

Add controlled read-only inspection support.

Default:

```env
RUNTIME_INSPECTION_COMMANDS_ENABLED=false
```

Command execution may occur only when both are true:

1. Request body sets `allow_read_only_commands=true`.
2. Environment sets `RUNTIME_INSPECTION_COMMANDS_ENABLED=true`.

Allowed command categories:

```text
pwd
whoami
hostname
date
ls
find
cat
grep
systemctl status
systemctl cat
systemctl list-timers
crontab -l
docker ps
docker compose ps
docker inspect
journalctl -n
```

The shell inspection service must:

1. Prefer argument lists, not command strings.
2. Reject shell metacharacters.
3. Reject non-allowlisted commands.
4. Reject sudo.
5. Reject write, edit, delete, install, restart, and network-scan commands.
6. Enforce timeouts.
7. Bound captured output.
8. Record skipped, rejected, completed, and failed commands as evidence.
9. Use `shell=False` unless a tightly justified safe exception exists.

If safe execution is too risky, implement only dry-run command planning. Do not add broad shell execution.

## Required Artifacts

For each runtime inspection, write:

```text
/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-task-packet.yaml
/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-agent-result.json
/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-report.md
/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-evidence.json
```

The report must include:

1. Project id.
2. Project name.
3. Original request.
4. Inspection target.
5. Runtime target type.
6. Commands planned.
7. Commands executed or skipped.
8. Evidence collected.
9. Execution-path findings.
10. Missing discovery requirements.
11. `safe_to_modify`.
12. Confidence.
13. Blockers.
14. Approval gate placeholder.
15. Next recommended step.

## Registry Behavior

Do not mutate global runtime registries in v0.4.

If registry updates are useful, write candidate updates only under the project workspace:

```text
/srv/ai-lab/projects/<project-id>/qa/candidate-runtime-registry-updates.yaml
```

Candidate registry updates must be clearly marked as proposals and must not be applied automatically.

## Database Requirements

Runtime-inspector runs must be tracked:

1. `runtime_inspector` task status moves `pending -> running -> complete` or `failed`.
2. `agent_runs` records the runtime-inspector run.
3. `events` records runtime inspection start and completion or failure.
4. `handoffs` records the runtime-inspection handoff if the existing schema supports it.

If schema changes are needed, add an idempotent migration. Do not drop data. Do not break v0.1, v0.2, or v0.3 upgrades.

## LLM Behavior

The runtime inspector may use the configured LLM if available, but must work without it.

If LLM is unavailable:

1. Runtime inspection still completes with deterministic output.
2. Workflow does not fail solely because Ollama is unavailable.
3. Fallback usage is recorded in `agent_runs`.

The LLM must not be allowed to execute or authorize arbitrary commands. Any suggested commands must pass the read-only allowlist before execution, and execution still requires the request flag plus environment flag.

## Documentation Requirements

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/security-model.md
```

Create:

```text
docs/v0.4-validation.md
```

Document:

1. Runtime inspector purpose.
2. Read-only behavior.
3. Execution-path mapping.
4. Discover-before-modify enforcement.
5. Runtime-inspect endpoint usage.
6. Command execution disabled by default.
7. How to enable read-only inspection commands.
8. Approval gate placeholders.
9. Validation commands.
10. Known limitations.
11. Future v0.5 modification approval workflow.

## Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required coverage:

1. Runtime-inspect endpoint exists.
2. Runtime-inspect returns structured JSON.
3. Runtime-inspect creates report files.
4. Runtime-inspect updates runtime_inspector task status.
5. Runtime-inspect writes an agent_runs row.
6. Discover-before-modify validator returns false when fields are missing.
7. Shell inspection rejects non-allowlisted commands.
8. Shell inspection does not run commands by default.
9. Runtime-inspect does not require live Ollama.
10. Runtime-inspect does not mutate `harness/prod`.

Tests must not require live Ollama, Docker, systemd, cron, or sudo.

## Validation Before PR Ready

Run:

```bash
python -m compileall orchestrator
cd orchestrator && python -m pytest
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check origin/main...HEAD
```

Do not claim Ubuntu install success unless actually tested on Ubuntu.

## Manual Ubuntu Validation Before Merge

Manual Ubuntu validation should confirm:

```text
PASS: sudo ./install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: GET /health returns ok
PASS: POST /projects creates a project
PASS: POST /projects/{project_id}/runtime-inspect returns structured JSON
PASS: runtime-inspector-task-packet.yaml is created
PASS: runtime-inspector-agent-result.json is created
PASS: runtime-inspection-report.md is created
PASS: runtime-inspection-evidence.json is created
PASS: runtime_inspector task status updates
PASS: agent_runs has runtime_inspector row
PASS: safe_to_modify is false when discovery is incomplete
PASS: harness/prod files are not modified
PASS: no live cron or service modification occurs
PASS: no sudo commands are executed
```

Optional validation with read-only command execution enabled:

```text
PASS: RUNTIME_INSPECTION_COMMANDS_ENABLED=true allows only allowlisted read-only commands
PASS: rejected commands are recorded
PASS: command outputs are captured and bounded
```

## Completion Criteria

The v0.4 PR is complete only when:

1. Runtime-inspect endpoint exists.
2. Runtime-inspector workflow runs.
3. Runtime-inspection task packet is written.
4. Runtime-inspection agent result is written.
5. Runtime-inspection report is written.
6. Runtime-inspection evidence JSON is written.
7. Runtime-inspector DB task is updated.
8. `agent_runs` records runtime-inspector activity.
9. Discover-before-modify validator exists.
10. Shell command execution is disabled by default.
11. Any command execution is read-only and allowlisted.
12. Global registries are not mutated.
13. `harness/prod` is not mutated.
14. No live modification exists.
15. Tests pass.
16. Docs are updated.

v0.4 is complete when the system can prove what should be inspected before modification, not when it can modify the runtime.
