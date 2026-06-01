# BUILD_DIRECTIVE_v0.7.md

# AI Lab Orchestrator — v0.7 Build Directive

## 1. Purpose

Build v0.7 of **AI Lab Orchestrator**.

v0.6 added approval status transitions and approved dry-run validation. It can validate approved plans, inspect patch safety, classify command plans, and confirm rollback requirements without modifying production.

v0.7 must add the next safety layer:

> Sandboxed execution environment for approved plans.

This release may apply candidate changes **only inside an isolated project sandbox**.

v0.7 must not modify production files, cron jobs, systemd units, global runtime registries, or production harness files.

---

## 2. Core Goal

Add a sandbox validation workflow that can:

1. load a project
2. load an approved approval record
3. confirm dry-run validation passed
4. create an isolated sandbox directory under the project folder
5. copy approved candidate artifacts into the sandbox
6. apply candidate patch only inside the sandbox
7. validate proposed commands without executing production-modifying commands
8. optionally execute harmless sandbox-local validation commands
9. capture sandbox logs and artifacts
10. compare sandbox output to expected outcome
11. write sandbox validation results
12. record events in PostgreSQL
13. keep production mutation blocked

---

## 3. Hard Safety Rules

v0.7 must not:

1. modify production files
2. edit cron jobs
3. edit systemd units
4. restart services
5. run sudo
6. install packages
7. delete production files
8. mutate `/srv/ai-lab/harness/prod`
9. mutate `/srv/ai-lab/runtime/registries`
10. execute modifying commands outside the sandbox
11. add arbitrary shell execution
12. perform network scanning
13. implement self-improvement
14. add a web UI
15. bypass approval or dry-run validation checks

This release is **sandboxed validation only**.

---

## 4. Required New Endpoint

Add:

```text
POST /projects/{project_id}/approvals/{approval_id}/sandbox-run
```

Request body:

```json
{
  "sandbox_mode": "patch_only|plan_only|full_sandbox",
  "allow_sandbox_commands": false
}
```

Defaults:

```text
sandbox_mode=full_sandbox
allow_sandbox_commands=false
```

Behavior:

* load project from PostgreSQL
* load approval record
* require approval status `approved`
* require prior dry-run validation result exists and passed
* create sandbox directory
* copy approved plan artifacts into sandbox
* apply patch inside sandbox only when safe
* do not apply patch to production
* validate command plan in sandbox-only mode
* write sandbox result artifacts
* record event rows
* return structured result

Required response shape:

```json
{
  "project_id": "",
  "approval_id": "",
  "status": "passed|failed|blocked",
  "sandbox_path": "",
  "sandbox_report_path": "",
  "sandbox_result_path": "",
  "production_modified": false,
  "global_registries_modified": false,
  "harness_modified": false,
  "commands_executed": [],
  "commands_blocked": [],
  "issues": [],
  "next_step": ""
}
```

---

## 5. Required Artifacts

Write all v0.7 artifacts under:

```text
/srv/ai-lab/projects/<project-id>/sandbox/
```

Required files:

```text
/srv/ai-lab/projects/<project-id>/sandbox/sandbox-run-report.md
/srv/ai-lab/projects/<project-id>/sandbox/sandbox-run-result.json
/srv/ai-lab/projects/<project-id>/sandbox/sandbox-command-log.json
/srv/ai-lab/projects/<project-id>/sandbox/sandbox-file-manifest.json
/srv/ai-lab/projects/<project-id>/sandbox/applied.patch
```

Also copy source artifacts into:

```text
/srv/ai-lab/projects/<project-id>/sandbox/input/
```

Expected copied files:

```text
modification-plan.md
modification-plan.json
dry-run.patch
dry-run-validation-result.json
patch-validation.json
```

Do not write outside the project folder except PostgreSQL event rows.

Do not mutate:

```text
/srv/ai-lab/runtime/registries/
/srv/ai-lab/harness/prod/
```

---

## 6. Sandbox Directory Rules

Create a deterministic sandbox root:

```text
/srv/ai-lab/projects/<project-id>/sandbox/
```

Inside it, create:

```text
input/
workspace/
output/
logs/
```

Rules:

* sandbox may be overwritten only for the same project and approval after recording previous result
* sandbox must not use symlinks that escape the project folder
* sandbox must reject path traversal
* sandbox must not copy `/etc`, `/usr`, `/var/spool/cron`, `/srv/ai-lab/harness/prod`, or `/srv/ai-lab/runtime/registries`
* sandbox must treat all production paths as references only
* sandbox must not mount host production directories

---

## 7. Patch Application Rules

v0.7 may apply a patch only if:

1. approval status is `approved`
2. dry-run validation previously passed
3. patch target paths are sandbox-local
4. patch does not target forbidden paths
5. patch does not escape the project sandbox
6. patch is candidate-only
7. patch application occurs inside `/srv/ai-lab/projects/<project-id>/sandbox/workspace`

If the patch cannot be safely applied, return:

```text
status=blocked
```

Never apply a patch directly to:

```text
/srv/ai-lab/harness/prod
/srv/ai-lab/runtime/registries
/etc
/usr
/var
/lib/systemd
/etc/systemd
/var/spool/cron
```

---

## 8. Command Handling Rules

v0.7 must not execute modifying commands against production.

If `allow_sandbox_commands=false`, no commands are executed. The system only writes a command validation report.

If `allow_sandbox_commands=true`, only sandbox-safe commands may execute, and only inside the sandbox.

Allowed sandbox command categories:

```text
pwd
ls
find
cat
grep
python3 -m py_compile
python3 -m compileall
bash -n
git apply --check
```

Blocked commands include:

```text
sudo *
systemctl *
service *
crontab *
apt *
dnf *
yum *
rm *
mv *
cp * /etc/*
docker compose up *
docker compose down *
docker run *
chmod *
chown *
curl *
wget *
ssh *
scp *
```

All blocked commands must be recorded in:

```text
sandbox-command-log.json
```

Commands must be executed without `shell=True` where practical.

All commands must have:

```text
timeout
cwd set to sandbox path
bounded stdout/stderr
exit code recorded
```

---

## 9. Required Services

Add:

```text
orchestrator/app/services/sandbox_service.py
orchestrator/app/services/sandbox_command_service.py
orchestrator/app/services/sandbox_patch_service.py
```

Suggested schema:

```text
orchestrator/app/schemas/sandbox_run.py
```

Keep implementation simple.

Do not add Docker-based sandboxing in v0.7 unless already trivial. A project-local filesystem sandbox is acceptable for v0.7.

Do not add Kubernetes.

Do not add multi-VM scheduling.

---

## 10. Database and Event Tracking

Use existing tables where practical.

Record events for:

```text
sandbox_run_started
sandbox_input_copied
sandbox_patch_validated
sandbox_patch_applied_or_blocked
sandbox_commands_validated
sandbox_run_completed
```

If schema changes are required, add an idempotent migration:

```text
db/migrations/006-v0.7-sandbox-run.sql
```

Do not drop data.

Do not break upgrades from v0.1 through v0.6.

---

## 11. LLM Behavior

v0.7 does not require LLM usage.

If LLM is used, it may only summarize sandbox validation findings.

The LLM must not:

* decide approval
* execute commands
* apply patches
* override deterministic validators
* override safety checks

Deterministic validation is authoritative.

---

## 12. Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required test coverage:

1. sandbox-run endpoint exists
2. sandbox-run requires approval status approved
3. sandbox-run requires prior dry-run validation passed
4. sandbox directory is created under project folder
5. source artifacts are copied into sandbox input folder
6. sandbox result artifacts are written
7. patch is not applied to production
8. forbidden patch targets are blocked
9. path traversal is blocked
10. global registry mutation is blocked
11. harness/prod mutation is blocked
12. no sudo command execution
13. no production system command execution
14. commands are not executed when `allow_sandbox_commands=false`
15. blocked commands are recorded
16. safe sandbox validation commands are allowed only when explicitly enabled
17. no live Ollama required

Tests must not require live Ollama.

Tests must not require sudo/systemd/Docker availability unless mocked.

---

## 13. Required Documentation

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/security-model.md
```

Create:

```text
docs/v0.7-validation.md
```

Document:

* sandbox-run endpoint
* sandbox artifact locations
* patch sandboxing behavior
* command restrictions
* approval/dry-run prerequisites
* forbidden paths
* what v0.7 explicitly does not do
* Ubuntu validation steps

---

## 14. Required Validation Commands

Before marking PR ready, run:

```bash
python -m compileall orchestrator
cd orchestrator && python -m pytest
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check origin/main...HEAD
```

Do not claim Ubuntu success unless tested on Ubuntu.

---

## 15. Ubuntu Manual Validation Before Merge

Manual Ubuntu validation must confirm:

```text
PASS: sudo ./install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: POST /projects creates project
PASS: POST /projects/{project_id}/runtime-inspect creates runtime inspection artifacts
PASS: POST /projects/{project_id}/modification-plan creates approval record
PASS: approval transition to approved works
PASS: dry-run validation passes
PASS: POST /projects/{project_id}/approvals/{approval_id}/sandbox-run runs after dry-run pass
PASS: sandbox artifacts are written under project folder
PASS: production_modified=false
PASS: global_registries_modified=false
PASS: harness_modified=false
PASS: no production files are modified
PASS: no global registry files are modified
PASS: no harness/prod files are modified
PASS: no sudo or live production modification occurs
```

---

## 16. Completion Criteria

The v0.7 PR is complete only when:

1. sandbox-run endpoint exists.
2. sandbox-run requires approved approval.
3. sandbox-run requires prior dry-run validation passed.
4. sandbox project directory is created.
5. source artifacts are copied into sandbox input.
6. sandbox result artifacts are written.
7. patch application is sandbox-only.
8. command execution is disabled by default.
9. command validation blocks unsafe commands.
10. no production modification occurs.
11. tests pass.
12. docs are updated.

---

## 17. Do Not Do These in v0.7

Do not implement:

* live production modification
* cron editing
* systemd editing
* service restart
* sudo/root execution
* package installation
* production harness mutation
* global registry mutation
* self-improvement
* web UI
* auth system
* arbitrary shell execution
* Docker sandboxing unless trivial and strictly isolated
* Kubernetes
* multi-VM scheduling
