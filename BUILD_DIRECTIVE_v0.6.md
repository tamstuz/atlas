# BUILD_DIRECTIVE_v0.6.md

# AI Lab Orchestrator — v0.6 Build Directive

## 1. Purpose

Build v0.6 of **AI Lab Orchestrator**.

v0.5 added approval-gated controlled modification planning. It can generate blocked or pending approval records and project-local modification plan artifacts, but it does not execute anything.

v0.6 must add the next safety layer:

> Approved dry-run execution and patch validation.

This release allows human-approved plans to be validated in dry-run mode only.

v0.6 must not perform live production modifications.

---

## 2. Core Goal

Add a dry-run validation workflow that can:

1. load a project
2. load an approval record
3. confirm the approval status
4. load the candidate modification plan artifacts
5. validate the dry-run patch structure
6. validate proposed command plans without executing modifying commands
7. validate rollback plan completeness
8. write dry-run validation artifacts
9. record validation results in PostgreSQL
10. keep all production mutation blocked

---

## 3. Hard Safety Rules

v0.6 must not:

1. apply patches to production files
2. edit cron jobs
3. edit systemd units
4. restart services
5. run sudo
6. install packages
7. delete files
8. mutate production harness files
9. mutate global runtime registries
10. execute modifying commands
11. add arbitrary shell execution
12. perform network scanning
13. implement self-improvement
14. add a web UI
15. bypass approval checks

This release is **dry-run validation only**.

---

## 4. Required New Endpoint: Approval Status Transition

Add:

```text
POST /projects/{project_id}/approvals/{approval_id}/status
```

Request body:

```json
{
  "status": "approved|rejected",
  "reason": ""
}
```

Behavior:

* load project from PostgreSQL
* load approval record
* confirm approval belongs to project
* allow status transition only from `pending` or `blocked`
* write approval status update
* write event row
* return updated approval record
* do not execute anything

Allowed transitions in v0.6:

```text
pending -> approved
pending -> rejected
blocked -> rejected
blocked -> approved only if allow_blocked_approval=true is explicitly provided
```

Optional request body:

```json
{
  "status": "approved",
  "reason": "",
  "allow_blocked_approval": false
}
```

Default:

```text
allow_blocked_approval=false
```

If a blocked approval is approved without `allow_blocked_approval=true`, return a clear error.

---

## 5. Required New Endpoint: Dry-Run Validation

Add:

```text
POST /projects/{project_id}/approvals/{approval_id}/dry-run
```

Request body:

```json
{
  "validation_mode": "patch_only|plan_only|full_dry_run"
}
```

Default:

```text
validation_mode=full_dry_run
```

Behavior:

* load project
* load approval record
* require approval status `approved`
* load modification plan artifacts
* load dry-run patch artifact
* validate patch syntax/structure without applying to production
* validate proposed commands are non-executed and still blocked if modifying
* validate rollback plan exists
* write dry-run validation result files
* record event rows
* return structured result
* never execute live modification

Required response shape:

```json
{
  "project_id": "",
  "approval_id": "",
  "status": "passed|failed|blocked",
  "validation_report_path": "",
  "patch_validation_path": "",
  "production_modified": false,
  "global_registries_modified": false,
  "harness_modified": false,
  "issues": [],
  "next_step": ""
}
```

---

## 6. Required Artifacts

Write all v0.6 artifacts under:

```text
/srv/ai-lab/projects/<project-id>/approvals/
```

Required files:

```text
/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-report.md
/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-result.json
/srv/ai-lab/projects/<project-id>/approvals/patch-validation.json
```

Do not write outside the project folder except PostgreSQL event/approval records.

Do not mutate:

```text
/srv/ai-lab/runtime/registries/
/srv/ai-lab/harness/prod/
```

---

## 7. Patch Validation Rules

The dry-run patch validator must:

1. read the project-local `dry-run.patch`
2. confirm it is present
3. confirm it is not empty unless the plan is blocked
4. confirm it does not target forbidden paths
5. confirm it does not target `/srv/ai-lab/harness/prod`
6. confirm it does not target `/srv/ai-lab/runtime/registries`
7. confirm it does not target `/etc`
8. confirm it does not target systemd unit locations
9. confirm it does not target cron locations
10. confirm it is candidate-only
11. never apply the patch

Forbidden patch target examples:

```text
/etc/*
/usr/lib/systemd/*
/etc/systemd/*
/var/spool/cron/*
/srv/ai-lab/harness/prod/*
/srv/ai-lab/runtime/registries/*
```

Allowed patch target examples for dry-run validation:

```text
/srv/ai-lab/projects/<project-id>/workspace/*
/srv/ai-lab/projects/<project-id>/approvals/*
```

If the patch targets forbidden paths, dry-run validation must return `blocked`.

---

## 8. Command Plan Validation Rules

If the modification plan contains proposed commands, v0.6 must validate them but not execute them.

Command validation must:

* identify modifying commands
* identify sudo commands
* identify service restart commands
* identify cron edit commands
* identify package installation commands
* identify file deletion commands
* classify each command as:

  * allowed_for_future_review
  * blocked
  * unknown
* record reasons

Blocked commands include:

```text
sudo *
systemctl restart *
systemctl stop *
systemctl start *
systemctl enable *
systemctl disable *
crontab -e
rm *
mv *
cp * /etc/*
apt install *
apt remove *
docker compose up *
docker compose down *
```

v0.6 must not run these commands.

---

## 9. Rollback Plan Validation

The dry-run validator must check whether the modification plan includes a rollback plan.

Return:

```json
{
  "rollback_plan_present": true,
  "rollback_plan_complete": false,
  "missing_rollback_items": []
}
```

Required rollback items:

```text
files affected
backup strategy
restore steps
verification after rollback
failure trigger
owner/human approval requirement
```

---

## 10. Services to Add

Suggested files:

```text
orchestrator/app/services/approval_transition_service.py
orchestrator/app/services/dry_run_validation_service.py
orchestrator/app/services/patch_validation_service.py
orchestrator/app/services/command_plan_validator.py
```

Suggested schema file:

```text
orchestrator/app/schemas/approval_status.py
```

Keep implementations simple.

Do not add a large policy engine.

---

## 11. Database Work

Use existing `approvals` and `events` tables where practical.

If schema changes are required, add an idempotent migration:

```text
db/migrations/005-v0.6-dry-run-validation.sql
```

Do not drop data.

Do not break upgrades from v0.1 through v0.5.

Required tracking:

* approval status transition
* transition reason
* dry-run validation started
* dry-run validation completed
* validation status
* validation artifact path

If using `events`, store the details in JSON.

---

## 12. LLM Behavior

v0.6 does not require LLM usage.

If LLM is used, it may only summarize validation findings.

The LLM must not:

* decide approval
* execute commands
* modify plans
* apply patches
* override safety checks

Deterministic validation must be the authority.

---

## 13. Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required test coverage:

1. approval status endpoint exists
2. pending approval can become approved
3. pending approval can become rejected
4. blocked approval cannot become approved unless explicitly allowed
5. dry-run endpoint requires approved status
6. dry-run validation writes artifacts
7. forbidden patch targets are blocked
8. harness/prod patch targets are blocked
9. global registry patch targets are blocked
10. sudo commands are classified as blocked
11. service restart commands are classified as blocked
12. rollback plan validation detects missing items
13. no patch is applied
14. no command is executed
15. no global registry mutation
16. no harness/prod mutation

Tests must not require live Ollama.

Tests must not require sudo/systemd/Docker availability unless mocked.

---

## 14. Required Documentation

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/security-model.md
```

Create:

```text
docs/v0.6-validation.md
```

Document:

* approval transition endpoint
* dry-run validation endpoint
* dry-run artifacts
* patch validation behavior
* command validation behavior
* rollback validation behavior
* forbidden paths
* what v0.6 explicitly does not do
* Ubuntu validation steps

---

## 15. Required Validation Commands

Before marking PR ready, run:

```bash
python -m compileall orchestrator
cd orchestrator && python -m pytest
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check origin/main...HEAD
```

Do not claim Ubuntu success unless tested on Ubuntu.

---

## 16. Ubuntu Manual Validation Before Merge

Manual Ubuntu validation must confirm:

```text
PASS: sudo ./install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: POST /projects creates project
PASS: POST /projects/{project_id}/runtime-inspect creates runtime inspection artifacts
PASS: POST /projects/{project_id}/modification-plan creates approval record
PASS: POST /projects/{project_id}/approvals/{approval_id}/status can approve pending approval
PASS: POST /projects/{project_id}/approvals/{approval_id}/dry-run validates approved plan
PASS: dry-run validation artifacts are written
PASS: forbidden patches are blocked
PASS: proposed modifying commands are classified but not executed
PASS: no production files are modified
PASS: no global registry files are modified
PASS: no harness/prod files are modified
PASS: no sudo or live modification occurs
```

---

## 17. Completion Criteria

The v0.6 PR is complete only when:

1. approval status endpoint exists.
2. dry-run endpoint exists.
3. approval transitions are enforced.
4. approved plans can be dry-run validated.
5. blocked/unapproved plans cannot be dry-run validated.
6. patch validation exists.
7. command plan validation exists.
8. rollback plan validation exists.
9. dry-run artifacts are written.
10. no execution occurs.
11. tests pass.
12. docs are updated.

---

## 18. Do Not Do These in v0.6

Do not implement:

* live modification
* approval execution
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
* multi-VM scheduling
