# BUILD_DIRECTIVE_v0.5.md

# AI Lab Orchestrator — v0.5 Build Directive

## 1. Purpose

Build v0.5 of **AI Lab Orchestrator**.

v0.4 added runtime inspection and read-only discover-before-modify planning. It proved that the system can inspect runtime paths, collect evidence, write inspection reports, and block modification when the execution path is not sufficiently proven.

v0.5 must add the next layer:

> Approval-gated controlled modification planning.

This release must generate **candidate modification plans** only. It must not execute live modifications.

---

## 2. Core Goal

Add a controlled planning workflow that can:

1. load a project
2. load the latest runtime inspection result
3. evaluate whether discovery evidence is sufficient
4. refuse to plan unsafe modifications when discovery is incomplete
5. generate a candidate modification plan when allowed
6. write candidate plan artifacts under the project folder
7. create approval records in PostgreSQL
8. expose approval status through API
9. preserve strict no-execution behavior
10. prepare for a future v0.6 approval-execution workflow without implementing execution now

---

## 3. Hard Safety Rules

v0.5 must not:

1. execute modifications
2. edit cron jobs
3. edit systemd units
4. restart services
5. run sudo
6. install packages
7. delete files
8. mutate production harness files
9. mutate global runtime registries
10. bypass runtime inspection
11. bypass approval gates
12. add a web UI
13. implement autonomous self-improvement
14. add arbitrary shell execution
15. perform network scanning

This release is **planning only**.

---

## 4. Required New Endpoint

Add:

```text
POST /projects/{project_id}/modification-plan
```

Request body:

```json
{
  "change_request": "",
  "target_type": "cron|systemd|script|docker|python|unknown",
  "target_hint": "",
  "allow_plan_with_blockers": false
}
```

Behavior:

* load the project from PostgreSQL
* load the latest runtime inspection evidence from the project folder
* evaluate `safe_to_modify`
* evaluate missing discovery requirements
* if `safe_to_modify=false` and `allow_plan_with_blockers=false`, return a blocked response
* if blocked, still write a blocked planning report explaining what is missing
* if allowed, generate a candidate plan only
* create a PostgreSQL approval record with status `pending`
* write project-local artifacts
* never execute the plan

Required response shape:

```json
{
  "project_id": "",
  "status": "blocked|pending_approval|failed",
  "approval_id": "",
  "safe_to_modify": false,
  "plan_path": "",
  "dry_run_patch_path": "",
  "approval_required": true,
  "blockers": [],
  "next_step": ""
}
```

---

## 5. Required Read Endpoint

Add:

```text
GET /projects/{project_id}/approvals
```

Returns approval records for the project.

Response shape:

```json
{
  "project_id": "",
  "approvals": [
    {
      "approval_id": "",
      "approval_type": "",
      "status": "",
      "artifact_path": "",
      "created_at": "",
      "updated_at": ""
    }
  ]
}
```

No approve/execute endpoint is required in v0.5.

---

## 6. Approval Records

Use the existing `approvals` table if possible.

If schema changes are needed, add an idempotent migration:

```text
db/migrations/004-v0.5-approval-gated-planning.sql
```

The approval record must track:

```text
project_id
approval_type
status
artifact_path
requested_by
created_at
updated_at
```

Allowed approval statuses:

```text
pending
blocked
approved
rejected
expired
```

For v0.5, new records should usually be:

```text
pending
```

or:

```text
blocked
```

Do not implement approval execution.

---

## 7. Required Artifact Files

Write all v0.5 artifacts under the project folder only.

Required directory:

```text
/srv/ai-lab/projects/<project-id>/approvals/
```

Required files:

```text
/srv/ai-lab/projects/<project-id>/approvals/modification-plan.md
/srv/ai-lab/projects/<project-id>/approvals/modification-plan.json
/srv/ai-lab/projects/<project-id>/approvals/dry-run.patch
/srv/ai-lab/projects/<project-id>/approvals/approval-request.json
```

If the request is blocked, still write:

```text
/srv/ai-lab/projects/<project-id>/approvals/blocked-modification-plan.md
/srv/ai-lab/projects/<project-id>/approvals/blocked-modification-plan.json
```

Do not write outside the project folder.

Do not mutate `/srv/ai-lab/runtime/registries`.

Do not mutate `/srv/ai-lab/harness/prod`.

---

## 8. Modification Plan Contents

The candidate modification plan must include:

```text
project id
project name
change request
target type
target hint
runtime inspection source
safe_to_modify status
missing discovery requirements
proposed files to change
proposed commands
proposed validation steps
rollback plan
risk rating
approval status
explicit statement that nothing was executed
```

The plan must distinguish between:

```text
evidence-backed facts
inferences
unknowns
blocked items
```

---

## 9. Dry-Run Patch Rules

v0.5 may generate a dry-run patch file, but:

* it must not apply the patch
* it must be stored under the project approvals folder
* it may be empty if not enough information exists
* it must include comments explaining why it is a candidate only
* it must not target production harness files
* it must not target global runtime registry files
* it must not target system files outside the project unless only as a proposed path

Preferred behavior:

```text
Generate an explanatory dry-run.patch placeholder unless there is enough evidence to produce a real patch.
```

---

## 10. Planning Service

Add:

```text
orchestrator/app/services/modification_planning_service.py
```

Responsibilities:

* load latest runtime inspection evidence
* evaluate discovery completeness
* generate blocked or pending plan
* write artifacts
* create approval record
* record event
* never execute modification

Add schema if useful:

```text
orchestrator/app/schemas/modification_plan.py
```

---

## 11. LLM Behavior

The modification planning service may use the configured LLM if available.

If LLM is unavailable:

* generate deterministic plan
* do not fail solely because Ollama is unavailable
* record fallback behavior

If LLM is available:

* prompt must include:

  * change request
  * runtime inspection summary
  * discover-before-modify requirements
  * safe-to-modify status
  * expected output structure

The LLM must not be allowed to execute commands.

The LLM must not decide approval.

The LLM may only draft a candidate plan.

---

## 12. DB / Event Tracking

Record:

* modification planning started
* modification planning blocked or pending approval
* approval record created
* artifact paths written

Use `events` table where practical.

Use `agent_runs` if the planning service uses an LLM or deterministic planner role.

Role name:

```text
modification_planner
```

If adding a task is useful, add a `modification_planner` task for the project.

---

## 13. Required Tests

Add or update tests under:

```text
orchestrator/tests/
```

Required test coverage:

1. modification-plan endpoint exists
2. blocked response when runtime inspection is missing
3. blocked response when `safe_to_modify=false` and `allow_plan_with_blockers=false`
4. plan artifacts are written under project approvals folder
5. approval record is created
6. approvals read endpoint returns records
7. dry-run patch is not applied
8. no global registry mutation
9. no harness/prod mutation
10. no command execution
11. deterministic fallback works without live Ollama

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
docs/v0.5-validation.md
```

Document:

* approval-gated planning purpose
* endpoint usage
* blocked vs pending approval behavior
* artifact locations
* approval records
* dry-run patch behavior
* what v0.5 explicitly does not do
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
PASS: POST /projects/{project_id}/modification-plan returns blocked when safe_to_modify=false
PASS: blocked planning artifacts are written
PASS: approval record is created with blocked or pending status
PASS: GET /projects/{project_id}/approvals returns approval record
PASS: no dry-run patch is applied
PASS: no global registry files are modified
PASS: no harness/prod files are modified
PASS: no sudo or live modification occurs
```

---

## 17. Completion Criteria

The v0.5 PR is complete only when:

1. modification-plan endpoint exists.
2. approvals read endpoint exists.
3. runtime inspection evidence is required.
4. blocked planning works.
5. candidate planning works when allowed.
6. approval record is created.
7. artifacts are written under project approvals folder.
8. no execution occurs.
9. tests pass.
10. docs are updated.

---

## 18. Do Not Do These in v0.5

Do not implement:

* approval execution
* live modification
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
