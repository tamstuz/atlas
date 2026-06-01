# BUILD_DIRECTIVE_v0.8.md

# AI Lab Orchestrator — v0.8 Build Directive

## 1. Purpose

Build v0.8 of **AI Lab Orchestrator**.

v0.7 added sandboxed execution validation for approved plans. It can copy candidate artifacts into a project-local sandbox, validate patches and command plans in sandbox-only mode, and still block all production modification.

v0.8 must add the next safety layer:

> Production change package and human execution checklist.

This release creates a complete package a human can review and manually execute.

v0.8 must not execute production changes.

---

## 2. Core Goal

Add a production change packaging workflow that can:

1. load a project
2. load an approved approval record
3. confirm dry-run validation passed
4. confirm sandbox validation passed
5. generate a project-local production change package
6. generate a human execution checklist
7. generate exact command plan for human review only
8. generate rollback checklist
9. generate pre-flight verification checklist
10. generate post-change verification checklist
11. create a final human approval record
12. record package generation in PostgreSQL/events
13. keep all production mutation blocked

---

## 3. Hard Safety Rules

v0.8 must not:

1. execute production commands
2. apply patches to production files
3. edit cron jobs
4. edit systemd units
5. restart services
6. run sudo
7. install packages
8. delete files
9. mutate `/srv/ai-lab/harness/prod`
10. mutate `/srv/ai-lab/runtime/registries`
11. execute modifying commands
12. add arbitrary shell execution
13. perform network scanning
14. implement self-improvement
15. add a web UI
16. bypass approval, dry-run, or sandbox validation checks

This release is **packaging only**.

---

## 4. Required New Endpoint

Add:

```text
POST /projects/{project_id}/approvals/{approval_id}/change-package
```

Request body:

```json
{
  "change_window": "",
  "operator": "",
  "notes": ""
}
```

Behavior:

* load project from PostgreSQL
* load approval record
* require approval status `approved`
* require prior dry-run validation result exists and passed
* require prior sandbox validation result exists and passed
* load modification plan artifacts
* load dry-run validation artifacts
* load sandbox validation artifacts
* generate production change package artifacts
* create final human approval record
* write event rows
* return structured result
* never execute production change

Required response shape:

```json
{
  "project_id": "",
  "approval_id": "",
  "status": "packaged|blocked|failed",
  "change_package_path": "",
  "execution_checklist_path": "",
  "rollback_checklist_path": "",
  "preflight_checklist_path": "",
  "postchange_checklist_path": "",
  "final_approval_id": "",
  "production_modified": false,
  "global_registries_modified": false,
  "harness_modified": false,
  "issues": [],
  "next_step": ""
}
```

---

## 5. Required Read Endpoint

Add:

```text
GET /projects/{project_id}/change-packages
```

Returns package records for the project.

Response shape:

```json
{
  "project_id": "",
  "change_packages": [
    {
      "approval_id": "",
      "final_approval_id": "",
      "status": "",
      "artifact_path": "",
      "created_at": "",
      "updated_at": ""
    }
  ]
}
```

If no dedicated table is added, this endpoint may read from `approvals` and/or `events`.

---

## 6. Required Artifacts

Write all v0.8 artifacts under:

```text
/srv/ai-lab/projects/<project-id>/change-package/
```

Required files:

```text
/srv/ai-lab/projects/<project-id>/change-package/production-change-package.md
/srv/ai-lab/projects/<project-id>/change-package/production-change-package.json
/srv/ai-lab/projects/<project-id>/change-package/human-execution-checklist.md
/srv/ai-lab/projects/<project-id>/change-package/exact-command-plan.md
/srv/ai-lab/projects/<project-id>/change-package/rollback-checklist.md
/srv/ai-lab/projects/<project-id>/change-package/preflight-checklist.md
/srv/ai-lab/projects/<project-id>/change-package/postchange-checklist.md
/srv/ai-lab/projects/<project-id>/change-package/final-approval-request.json
/srv/ai-lab/projects/<project-id>/change-package/source-artifact-manifest.json
```

Copy source artifacts into:

```text
/srv/ai-lab/projects/<project-id>/change-package/source/
```

Expected copied files when present:

```text
modification-plan.md
modification-plan.json
dry-run.patch
dry-run-validation-result.json
patch-validation.json
sandbox-run-result.json
sandbox-run-report.md
sandbox-file-manifest.json
sandbox-command-log.json
```

Do not write outside the project folder except PostgreSQL records.

Do not mutate:

```text
/srv/ai-lab/runtime/registries/
/srv/ai-lab/harness/prod/
```

---

## 7. Production Change Package Contents

The production change package must include:

```text
project id
project name
approval id
change request
change window
operator
target type
target hint
runtime inspection summary
dry-run validation summary
sandbox validation summary
evidence-backed facts
inferences
unknowns
risk rating
production impact
exact files proposed for change
exact commands proposed for human execution
pre-flight checklist
execution checklist
rollback checklist
post-change checklist
final approval status
explicit statement that nothing was executed
```

The package must distinguish between:

```text
evidence-backed facts
inferences
unknowns
blocked items
human-required steps
```

---

## 8. Human Execution Checklist

The human checklist must include:

```text
confirm maintenance window
confirm backup/snapshot completed
confirm current service status
confirm exact target file paths
confirm exact command paths
confirm rollback owner
confirm rollback command/path
confirm post-change validation command
confirm who is executing the change
confirm who is approving the change
confirm no autonomous execution is active
```

---

## 9. Exact Command Plan Rules

v0.8 may write exact commands for human review, but:

* it must not execute them
* it must mark them as human-only
* it must include warnings for dangerous commands
* it must classify commands as:

  * informational
  * modifying
  * privileged
  * blocked_for_agent
  * human_only
* it must never pass commands to a shell runner
* it must never call the command execution services

Any command containing these patterns must be marked `blocked_for_agent` and `human_only`:

```text
sudo
systemctl restart
systemctl start
systemctl stop
systemctl enable
systemctl disable
service restart
crontab -e
apt install
apt remove
rm
mv
cp /etc
docker compose up
docker compose down
docker run
chmod
chown
```

---

## 10. Final Human Approval Record

Create a final approval record with:

```text
approval_type = production_change_package
status = pending
artifact_path = /srv/ai-lab/projects/<project-id>/change-package/production-change-package.md
```

This is not execution approval. It is only approval to mark the package as reviewed.

Do not implement execution.

Do not add an endpoint that executes an approved production change.

---

## 11. Required Services

Suggested files:

```text
orchestrator/app/services/change_package_service.py
orchestrator/app/services/human_checklist_service.py
orchestrator/app/services/command_classification_service.py
```

Suggested schema:

```text
orchestrator/app/schemas/change_package.py
```

Keep implementation simple.

Do not add a large policy engine.

---

## 12. Database and Event Tracking

Use existing `approvals` and `events` tables where practical.

Record events for:

```text
change_package_started
change_package_sources_loaded
change_package_generated
final_approval_created
change_package_blocked
```

If schema changes are required, add an idempotent migration:

```text
db/migrations/007-v0.8-change-package.sql
```

Do not drop data.

Do not break upgrades from v0.1 through v0.7.

---

## 13. LLM Behavior

v0.8 does not require LLM usage.

If LLM is used, it may only help draft human-readable package text.

The LLM must not:

* decide approval
* execute commands
* modify plans
* apply patches
* override deterministic validators
* override safety checks

Deterministic validation and approval status are authoritative.

---

## 14. Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required test coverage:

1. change-package endpoint exists
2. change-package requires approval status approved
3. change-package requires dry-run validation passed
4. change-package requires sandbox validation passed
5. change-package writes all required artifacts
6. source artifacts are copied into change-package/source
7. final approval record is created with status pending
8. GET /projects/{project_id}/change-packages returns package records
9. exact command plan is generated but not executed
10. dangerous commands are classified as blocked_for_agent and human_only
11. no production files are modified
12. no global registry mutation
13. no harness/prod mutation
14. no sudo execution
15. no live Ollama required

Tests must not require live Ollama.

Tests must not require sudo/systemd/Docker availability unless mocked.

---

## 15. Required Documentation

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/security-model.md
```

Create:

```text
docs/v0.8-validation.md
```

Document:

* change-package endpoint
* change-package artifacts
* human execution checklist
* exact command plan classification
* final approval record
* prerequisite chain
* forbidden agent behavior
* what v0.8 explicitly does not do
* Ubuntu validation steps

---

## 16. Required Validation Commands

Before marking PR ready, run:

```bash
python -m compileall orchestrator
cd orchestrator && python -m pytest
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check origin/main...HEAD
```

Do not claim Ubuntu success unless tested on Ubuntu.

---

## 17. Ubuntu Manual Validation Before Merge

Manual Ubuntu validation must confirm:

```text
PASS: sudo ./install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: POST /projects creates project
PASS: POST /projects/{project_id}/runtime-inspect creates runtime inspection artifacts
PASS: POST /projects/{project_id}/modification-plan creates approval record
PASS: approval transition to approved works
PASS: dry-run validation passes
PASS: sandbox-run passes
PASS: POST /projects/{project_id}/approvals/{approval_id}/change-package generates package
PASS: GET /projects/{project_id}/change-packages returns package record
PASS: change package artifacts are written under project folder
PASS: final approval record is created with status pending
PASS: exact command plan is written but not executed
PASS: production_modified=false
PASS: global_registries_modified=false
PASS: harness_modified=false
PASS: no production files are modified
PASS: no global registry files are modified
PASS: no harness/prod files are modified
PASS: no sudo or live production modification occurs
```

---

## 18. Completion Criteria

The v0.8 PR is complete only when:

1. change-package endpoint exists.
2. change-package requires approved approval.
3. change-package requires dry-run validation passed.
4. change-package requires sandbox validation passed.
5. change package directory is created.
6. required artifacts are written.
7. source artifacts are copied.
8. exact command plan is generated but not executed.
9. dangerous commands are classified.
10. final approval record is created.
11. no execution occurs.
12. tests pass.
13. docs are updated.

---

## 19. Do Not Do These in v0.8

Do not implement:

* live production modification
* production command execution
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
* Docker sandboxing
* Kubernetes
* multi-VM scheduling
