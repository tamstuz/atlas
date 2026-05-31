# BUILD_DIRECTIVE_v0.4.md

# AI Lab Orchestrator — v0.4 Build Directive

## 1. Purpose

Build v0.4 of **AI Lab Orchestrator**.

v0.3 successfully added:

* live external Ollama-backed specialist execution
* deterministic fallback when Ollama is unavailable
* prompt assembly from harness role files and task packets
* agent run metadata
* model/provider/fallback tracking
* real analyst, architect, developer, QA, and final report LLM calls

v0.4 must focus on the original reliability failure this project is intended to solve:

> Agents must not guess where runtime files, cron jobs, services, scripts, or source files live.
> They must inspect, trace, map, and prove the execution path before any modification is proposed.

This release adds a **runtime inspector** and **controlled execution planning** layer.

v0.4 is read-only. It must not perform live file modifications, cron edits, service edits, or sudo/root actions.

---

## 2. Core Goal

Add a real runtime-inspector workflow that can:

1. inspect a project request
2. determine whether runtime inspection is needed
3. create a runtime-inspection task packet
4. load runtime-inspector harness rules
5. generate an execution-path inspection plan
6. optionally run safe read-only inspection commands
7. write structured runtime-inspection results
8. update DB task/run state
9. create/update runtime registry records where appropriate
10. block modification until discover-before-modify requirements are satisfied

---

## 3. Required Design Principles

Follow these rules exactly:

1. The orchestrator orchestrates only.
2. The runtime inspector may inspect but must not modify.
3. All runtime inspection must follow `discover-before-modify.md`.
4. All filesystem references must use absolute paths.
5. No live cron modification in v0.4.
6. No live systemd service modification in v0.4.
7. No sudo/root-capable autonomous agent behavior in v0.4.
8. No autonomous self-improvement in v0.4.
9. No web UI in v0.4.
10. No production harness mutation.
11. No bypassing harness policy.
12. No arbitrary shell command execution.
13. Only explicitly allowlisted read-only commands may run.
14. All command output must be recorded.
15. All runtime-inspection conclusions must include confidence and evidence.
16. All unresolved findings must be marked as blockers or unknowns.

---

## 4. Branch / PR Behavior

Build v0.4 in a new branch.

Suggested branch name:

```text
codex/v0.4-runtime-inspector
```

Open a PR linked to the v0.4 issue.

The PR must include:

* summary of changes
* test commands run
* Ubuntu validation instructions
* known limitations
* recommended v0.5 issues

Do not merge directly to main.

---

## 5. Required New/Updated Endpoints

Add:

```text
POST /projects/{project_id}/runtime-inspect
```

Behavior:

* loads project from PostgreSQL
* loads project filesystem state
* loads runtime-inspector role file
* loads required runtime-control harness files
* creates or updates the `runtime_inspector` task
* runs the runtime-inspector workflow
* writes task packet
* writes agent result
* writes runtime inspection report
* updates DB task/run state
* returns structured JSON

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

In v0.4, `safe_to_modify` should usually be `false` unless all discover-before-modify requirements are satisfied.

Even if `safe_to_modify=true`, v0.4 must not perform modification.

---

## 6. Runtime Inspector Workflow

Add or update:

```text
orchestrator/app/nodes/runtime_inspector.py
orchestrator/app/services/runtime_inspection_service.py
```

The runtime inspector should:

1. determine the runtime target type if possible:

   * cron
   * systemd service
   * script
   * Docker Compose service
   * Python app
   * unknown

2. generate a required discovery checklist

3. run only safe read-only commands where allowed

4. collect evidence

5. produce structured output

6. write artifacts

7. update DB state

---

## 7. Required Harness Files

Use existing files where possible.

Must load:

```text
harness/prod/roles/runtime-inspector.md
harness/prod/runtime-control/discover-before-modify.md
harness/prod/runtime-control/absolute-path-policy.md
harness/prod/runtime-control/cron-debug-policy.md
harness/prod/runtime-control/service-debug-policy.md
harness/prod/workflow-rules/handoff-policy.md
harness/prod/workflow-rules/completion-gates.md
```

If needed, update `runtime-inspector.md` only to clarify read-only behavior.

Do not weaken existing harness policy.

Do not allow production harness mutation.

---

## 8. Discover-Before-Modify Enforcement

Create a reusable validator.

Suggested file:

```text
orchestrator/app/services/discovery_validator.py
```

It must evaluate whether the inspection has identified:

1. scheduler/source
2. exact command
3. runtime working directory
4. absolute script path
5. config files
6. log files
7. verification command
8. owner/service context
9. current observed behavior
10. proposed next step

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

In v0.4 this validator is only for reporting and gating future modification workflows. It must not execute modifications.

---

## 9. Read-Only Shell Inspection

Add a controlled command runner for read-only inspection.

Suggested file:

```text
orchestrator/app/services/shell_inspection_service.py
```

This service must:

* execute only allowlisted commands
* reject commands not on the allowlist
* reject shell metacharacters unless explicitly safe
* enforce timeout
* capture stdout/stderr/exit code
* write command evidence to the runtime inspection report
* never use sudo
* never write files
* never restart services
* never edit cron
* never edit systemd
* never install packages

Allowed command categories for v0.4:

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

Important:

* If implementing allowlisted shell execution is too risky or too large, implement a dry-run command plan instead.
* Do not add broad shell execution.
* Do not add arbitrary command execution.

Preferred v0.4 behavior:

```text
Default: generate inspection plan only
Optional: execute read-only commands if explicitly enabled by env
```

Add environment variable:

```env
RUNTIME_INSPECTION_COMMANDS_ENABLED=false
```

Default must be `false`.

---

## 10. Runtime Inspection Artifacts

For each runtime inspection, write:

```text
/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-task-packet.yaml
/srv/ai-lab/projects/<project-id>/handoffs/runtime-inspector-agent-result.json
/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-report.md
/srv/ai-lab/projects/<project-id>/qa/runtime-inspection-evidence.json
```

The report must include:

```text
project id
project name
original request
inspection target
runtime target type
commands planned
commands executed
evidence collected
execution path findings
missing discovery requirements
safe_to_modify
confidence
blockers
next recommended step
```

---

## 11. Runtime Registry Updates

Use existing registry files under:

```text
/srv/ai-lab/runtime/registries/
```

v0.4 may create/update:

```text
execution-map.yaml
service-registry.yaml
cron-registry.yaml
```

But only if the inspection evidence is strong enough.

Registry updates must:

* be append/update only
* preserve existing entries
* include project_id and timestamp
* include evidence references
* not overwrite unrelated records
* not claim certainty without evidence

If registry writing is risky, write candidate registry updates under the project folder instead:

```text
/srv/ai-lab/projects/<project-id>/qa/candidate-runtime-registry-updates.yaml
```

Preferred v0.4 behavior:

```text
Write candidate registry updates, not global registry mutations.
```

---

## 12. Database Work

Update DB usage so runtime-inspector runs are tracked.

Required:

* `runtime_inspector` task status updates from `pending` to `running` to `complete` or `failed`
* `agent_runs` row written for runtime inspector
* `events` row written for runtime inspection started/completed
* `handoffs` row written if current schema supports it

If schema changes are needed, add an idempotent migration:

```text
db/migrations/003-v0.4-runtime-inspector.sql
```

Do not drop data.

Do not break v0.1, v0.2, or v0.3 upgrades.

---

## 13. LLM Behavior

The runtime inspector may use the configured LLM if available.

If LLM is unavailable:

* runtime-inspector must still produce deterministic inspection plan
* workflow must not fail solely because Ollama is unavailable
* fallback_used must be recorded in `agent_runs`

If LLM is available:

* prompt must include runtime-inspector role file
* prompt must include discover-before-modify policy
* prompt must include absolute-path policy
* prompt must include task packet
* prompt must require structured output

Do not allow the LLM to decide to run arbitrary commands.

The LLM may suggest commands, but the command runner must enforce allowlist and read-only behavior.

---

## 14. Runtime Inspection Request Body

`POST /projects/{project_id}/runtime-inspect` may accept optional JSON:

```json
{
  "target_type": "cron|systemd|script|docker|python|unknown",
  "target_hint": "",
  "allow_read_only_commands": false
}
```

Behavior:

* `target_type` defaults to `unknown`
* `target_hint` is optional
* `allow_read_only_commands` defaults to false
* even if true, global env `RUNTIME_INSPECTION_COMMANDS_ENABLED` must also be true
* if either is false, command execution is skipped and only a command plan is generated

---

## 15. Security Requirements

Hard requirements:

1. No sudo.
2. No write commands.
3. No package installation.
4. No service restart.
5. No cron edit.
6. No systemd edit.
7. No file deletion.
8. No network scanning.
9. No arbitrary command string passed directly to shell.
10. No shell=True unless heavily justified and safe.
11. Commands must be passed as argument lists where practical.
12. Command outputs must be bounded/truncated.
13. Timeouts required.
14. Any rejected command must be recorded as rejected.

---

## 16. Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required test coverage:

1. runtime-inspect endpoint exists
2. runtime-inspect returns structured JSON
3. runtime-inspect creates report files
4. runtime-inspect updates runtime_inspector task status
5. runtime-inspect writes agent_runs row
6. discover-before-modify validator returns false when required fields are missing
7. shell inspection service rejects non-allowlisted commands
8. shell inspection service does not run commands by default
9. runtime-inspect does not require live Ollama
10. runtime-inspect does not mutate harness/prod

Tests must not require live Ollama.

Tests must not require real Docker/systemd availability unless mocked.

---

## 17. Required Documentation Updates

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/security-model.md
docs/v0.4-validation.md
```

Create:

```text
docs/v0.4-validation.md
```

Document:

* purpose of runtime inspector
* read-only behavior
* discover-before-modify enforcement
* endpoint usage
* default command execution disabled
* how to enable read-only inspection commands
* validation commands
* known limitations
* future v0.5 modification approval workflow

---

## 18. Required Validation Commands

Before marking PR ready, run:

```bash
python -m compileall orchestrator
cd orchestrator && python -m pytest
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check origin/main...HEAD
```

Do not claim Ubuntu install success unless actually tested on Ubuntu.

---

## 19. Ubuntu Manual Validation Before Merge

Manual Ubuntu validation must confirm:

```text
PASS: sudo ./install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: GET /health returns ok
PASS: POST /projects creates a project
PASS: POST /projects/{project_id}/runtime-inspect returns structured JSON
PASS: runtime-inspection-report.md is created
PASS: runtime-inspection-evidence.json is created
PASS: runtime_inspector task status updates
PASS: agent_runs has runtime_inspector row
PASS: safe_to_modify is false when discovery is incomplete
PASS: no harness/prod files are modified
PASS: no live cron/service modification occurs
PASS: no sudo commands are executed
```

Optional validation with read-only command execution enabled:

```text
PASS: RUNTIME_INSPECTION_COMMANDS_ENABLED=true allows only allowlisted read-only commands
PASS: rejected commands are recorded as rejected
PASS: command outputs are captured and bounded
```

---

## 20. Completion Criteria

The v0.4 PR is complete only when:

1. runtime-inspect endpoint exists.
2. runtime-inspector workflow runs.
3. runtime-inspection task packet is written.
4. runtime-inspection agent result is written.
5. runtime-inspection report is written.
6. runtime-inspection evidence JSON is written.
7. runtime_inspector DB task is updated.
8. agent_runs records runtime_inspector activity.
9. discover-before-modify validator exists.
10. shell command execution is disabled by default.
11. if command execution exists, it is read-only and allowlisted.
12. no production harness mutation exists.
13. no live modification exists.
14. tests pass.
15. docs are updated.

---

## 21. Do Not Do These in v0.4

Do not implement:

* live cron editing
* live systemd editing
* service restart
* sudo/root execution
* autonomous package install
* autonomous file modification
* web UI
* authentication system
* self-improvement workflow
* skill creation/promotion
* marketplace/plugin system
* network scanning
* arbitrary shell execution
* multi-VM scheduling
* approval-based modification execution

v0.4 is inspection and planning only.
