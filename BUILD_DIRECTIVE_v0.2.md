# BUILD_DIRECTIVE_v0.2.md

# AI Lab Orchestrator — v0.2 Build Directive

## 1. Purpose

Build v0.2 of **AI Lab Orchestrator**.

v0.1 successfully created the installable scaffold:

* FastAPI front-door API
* LangGraph placeholder workflow
* PostgreSQL container
* Qdrant container
* harness/prod and harness/candidate structure
* runtime registries
* project workspace creation
* systemd services
* healthcheck/doctor scripts
* optional external Ollama configuration

v0.2 must turn the scaffold into a basic working orchestrator.

The goal is to add:

1. PostgreSQL-backed project records
2. PostgreSQL-backed task records
3. LangGraph checkpoint persistence
4. real harness role loading per workflow node
5. external Ollama connection test endpoint
6. runtime-inspector specialist node
7. first real task execution flow:
   Intake → Analyst → Architect → Developer → QA → Final Report
8. structured task packet and agent result files per project

Keep this version focused. Do not build the full autonomous company system yet.

---

## 2. Core Design Rule

The orchestrator must orchestrate only.

It should:

* create project records
* create task records
* route workflow steps
* load the correct harness role file per node
* write task packets
* write agent result files
* update task/project status
* generate a final report

It should not:

* directly modify production harness files
* autonomously create new skills
* bypass the harness
* create sudo/root-capable agents
* install new system packages during workflow execution
* perform live cron/service edits
* add a web UI
* add authentication
* add Kubernetes
* overbuild beyond this directive

---

## 3. Required Branch / PR Behavior

Build v0.2 in a new branch.

Suggested branch name:

```text
codex/v0.2-db-backed-orchestration
```

Open a PR linked to issue #2.

The PR must include:

* summary of changes
* test commands run
* known limitations
* Ubuntu upgrade/install notes
* recommended v0.3 issues

Do not merge directly to main.

---

## 4. Required Database Work

v0.1 includes `db/init.sql`.

For v0.2, update the DB layer so the app actually uses PostgreSQL for project/task tracking.

### Required tables

Use existing tables where possible. Update schema only if necessary.

At minimum, the application must use:

```text
projects
tasks
agent_runs
handoffs
events
```

### Required behavior

When `POST /projects` is called:

1. create filesystem project workspace under `/srv/ai-lab/projects/<project-id>/`
2. create a `projects` row in PostgreSQL
3. create initial task rows in PostgreSQL
4. write `project-state.json`
5. write `task-board.json`
6. write `decision-log.md`

### Required project statuses

Use these statuses:

```text
new
running
blocked
complete
failed
```

### Required task statuses

Use these statuses:

```text
pending
running
complete
failed
blocked
```

### Required task roles

Create task rows for these roles:

```text
intake
analyst
architect
developer
qa
final_report
```

Also add:

```text
runtime_inspector
```

but it does not need to run in the default workflow unless explicitly triggered.

---

## 5. Database Access Layer

Create or update a clean database service layer.

Suggested files:

```text
orchestrator/app/services/project_service.py
orchestrator/app/services/task_service.py
orchestrator/app/services/run_service.py
orchestrator/app/db.py
```

Requirements:

* use `psycopg`
* use `.env` values for DB connection
* do not hard-code DB credentials
* fail clearly when database is unreachable
* avoid large ORM frameworks for v0.2
* keep SQL readable
* keep the implementation simple

Do not add SQLAlchemy unless necessary.

---

## 6. LangGraph Checkpoint Persistence

Add LangGraph checkpoint persistence.

Goal:

* workflow state should not live only in memory
* project workflow state should be resumable
* each project should have a stable workflow thread ID

Required behavior:

```text
thread_id = project_id
```

Use PostgreSQL-backed checkpointing if practical within the existing dependency stack.

If PostgreSQL checkpointing requires an additional dependency, add it only if it is stable and document the reason.

If full PostgreSQL checkpointing is too large for v0.2, implement a clear minimal fallback:

* persist graph state snapshots to PostgreSQL `events` or `agent_runs`
* document the limitation
* create a v0.3 TODO for formal LangGraph checkpoint saver

Do not fake persistence. If it is only snapshot persistence, say so clearly in docs and PR notes.

---

## 7. Harness Role Loading

v0.1 created harness role files under:

```text
/srv/ai-lab/harness/prod/roles/
```

v0.2 must load real role instructions per workflow node.

Required role file mapping:

```text
intake          -> harness/prod/roles/orchestrator.md
analyst         -> harness/prod/roles/analyst.md
architect       -> harness/prod/roles/architect.md
developer       -> harness/prod/roles/developer.md
qa              -> harness/prod/roles/qa.md
final_report    -> harness/prod/roles/final-report-writer.md
runtime_inspector -> harness/prod/roles/runtime-inspector.md
```

If `runtime-inspector.md` does not exist, create it.

### Harness loader requirements

Create/update:

```text
orchestrator/app/services/harness_loader.py
```

It must:

* use `HARNESS_DIR` from `.env`
* load role files by role name
* fail clearly if a role file is missing
* not load the entire harness into every node
* return only the role file and required shared rules for the active node

At minimum, also load:

```text
harness/prod/workflow-rules/handoff-policy.md
harness/prod/workflow-rules/completion-gates.md
```

For `runtime_inspector`, also load:

```text
harness/prod/runtime-control/discover-before-modify.md
harness/prod/runtime-control/absolute-path-policy.md
```

---

## 8. Structured Task Packets

For each workflow node, write a task packet file.

Location:

```text
/srv/ai-lab/projects/<project-id>/handoffs/<step-number>-<role>-task-packet.yaml
```

Example:

```text
/srv/ai-lab/projects/<project-id>/handoffs/01-intake-task-packet.yaml
/srv/ai-lab/projects/<project-id>/handoffs/02-analyst-task-packet.yaml
/srv/ai-lab/projects/<project-id>/handoffs/03-architect-task-packet.yaml
```

Task packet must include:

```yaml
project_id:
task_id:
role:
phase:
objective:
input_summary:
harness_files_loaded:
allowed_scope:
forbidden_actions:
expected_output:
definition_of_done:
created_at:
```

Use the existing schema file where practical:

```text
harness/prod/schemas/task-packet.schema.json
```

Update the schema if needed.

---

## 9. Structured Agent Result Files

For each workflow node, write an agent result file.

Location:

```text
/srv/ai-lab/projects/<project-id>/handoffs/<step-number>-<role>-agent-result.json
```

Required fields:

```json
{
  "project_id": "",
  "task_id": "",
  "role": "",
  "status": "",
  "summary": "",
  "artifacts_created": [],
  "files_read": [],
  "files_written": [],
  "harness_files_loaded": [],
  "next_recommended_role": "",
  "blockers": [],
  "created_at": ""
}
```

Use the existing schema file where practical:

```text
harness/prod/schemas/agent-result.schema.json
```

Update the schema if needed.

---

## 10. First Real Specialist Workflow

The default workflow should run:

```text
Intake → Analyst → Architect → Developer → QA → Final Report
```

For v0.2, specialist nodes may use deterministic placeholder output if no LLM endpoint is available.

But each node must:

1. load its harness role file
2. write a task packet
3. write an agent result file
4. update the task status in PostgreSQL
5. update project state
6. pass structured state to the next node

### Required default behavior without LLM

If external Ollama is unavailable, the workflow must still run using deterministic placeholder outputs.

Example:

```text
Analyst result: "Placeholder analyst result generated because LLM endpoint is unavailable."
```

Do not block the workflow only because Ollama is unavailable.

### Required behavior with LLM

If `OLLAMA_ENABLED=true` and the endpoint is available, the node may call the model.

Keep prompts simple.

Prompt should include:

* role instructions
* task packet
* project request
* required output schema

If LLM call fails, record the failure in the agent result and fall back to deterministic placeholder output unless the failure is fatal.

---

## 11. Runtime Inspector Node

Add a runtime-inspector specialist node.

It should not run by default in every project workflow unless explicitly requested.

Required file:

```text
orchestrator/app/nodes/runtime_inspector.py
```

Required role file:

```text
harness/prod/roles/runtime-inspector.md
```

Runtime inspector purpose:

* inspect runtime paths
* trace cron/service/process execution
* enforce discover-before-modify
* report exact source files before modification

For v0.2, the runtime inspector does not need to execute shell commands.

It should generate a structured inspection plan based on the harness policy.

Do not implement live cron editing.

Do not implement service modification.

---

## 12. External Ollama Connection Test Endpoint

Add endpoint:

```text
GET /llm/status
```

Behavior:

* read `OLLAMA_ENABLED`
* read `OLLAMA_BASE_URL`
* read `DEFAULT_MODEL`
* if Ollama disabled, return disabled status
* if enabled, test the configured endpoint
* do not crash if endpoint is unreachable
* return clear JSON

Example response when disabled:

```json
{
  "enabled": false,
  "provider": "ollama",
  "status": "disabled"
}
```

Example response when unreachable:

```json
{
  "enabled": true,
  "provider": "ollama",
  "base_url": "http://ollama.example.local:11434",
  "default_model": "gemma4:26b",
  "status": "unreachable",
  "error": "connection failed"
}
```

Example response when reachable:

```json
{
  "enabled": true,
  "provider": "ollama",
  "base_url": "http://ollama.example.local:11434",
  "default_model": "gemma4:26b",
  "status": "ok"
}
```

---

## 13. New Workflow Run Endpoint

Add endpoint:

```text
POST /projects/{project_id}/run
```

Behavior:

* loads project from PostgreSQL
* runs the default workflow
* writes task packets
* writes agent results
* updates DB task statuses
* writes final report
* returns final workflow state

If the project does not exist, return 404.

If project files are missing, return a clear error.

---

## 14. Project Read Endpoint Update

Update:

```text
GET /projects/{project_id}
```

It should return:

* project metadata from PostgreSQL
* filesystem paths
* task summary
* latest project status
* final report path if present

---

## 15. Final Report

The final report node must create:

```text
/srv/ai-lab/projects/<project-id>/final/final-report.md
```

Report should include:

```text
project id
project name
original request
workflow steps completed
task statuses
artifacts created
known limitations
next recommended step
```

This report may use deterministic content in v0.2.

---

## 16. Project State and Task Board Files

Maintain these files:

```text
project-state.json
task-board.json
decision-log.md
```

After workflow run:

### `project-state.json`

Should include:

```json
{
  "project_id": "",
  "name": "",
  "request": "",
  "status": "",
  "current_phase": "",
  "created_at": "",
  "updated_at": "",
  "final_report_path": ""
}
```

### `task-board.json`

Should include all tasks with:

```json
{
  "task_id": "",
  "role": "",
  "status": "",
  "started_at": "",
  "completed_at": ""
}
```

### `decision-log.md`

Append workflow decisions such as:

```text
- Created project
- Ran intake
- Ran analyst
- Ran architect
- Ran developer
- Ran QA
- Generated final report
```

---

## 17. Installation Compatibility

Do not break v0.1 install behavior.

The existing install validation must still pass:

```text
sudo ./install.sh
cd /srv/ai-lab
scripts/healthcheck.sh
curl http://localhost:8088/health
```

If DB migrations are added, install must run them safely.

The installer must remain idempotent where practical.

---

## 18. Required Tests

Add or update lightweight tests.

Suggested location:

```text
orchestrator/tests/
```

Required test coverage:

1. health endpoint
2. project creation endpoint
3. LLM status endpoint disabled/unreachable behavior
4. workflow run creates task packets
5. workflow run creates agent result files
6. final report file created
7. DB project/task records are created where practical

Tests should not require live Ollama.

Tests should not require Docker if impractical in the Codex environment. Mock DB or use temporary filesystem where reasonable.

If full DB integration tests are not practical in Codex, provide clear manual Ubuntu validation steps in README or PR notes.

---

## 19. Required Documentation Updates

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/install.md
docs/self-improvement.md
docs/security-model.md
```

At minimum, document:

* v0.2 workflow
* DB-backed project/task state
* `/projects/{project_id}/run`
* `/llm/status`
* task packet files
* agent result files
* final report location
* runtime inspector role
* Ollama optional behavior
* known limitations

---

## 20. Required Validation Commands

Before PR is marked ready, run and report:

```bash
python -m compileall orchestrator
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check
```

Also run available Python tests:

```bash
cd orchestrator
source .venv/bin/activate 2>/dev/null || true
python -m pytest
```

If pytest is not installed, either add it as a dev/test dependency or document the alternative test command.

Do not claim Ubuntu install success unless tested on Ubuntu.

---

## 21. Ubuntu Manual Validation Required Before Merge

After Codex opens PR, manual validation on Ubuntu must confirm:

```text
PASS: install.sh completes
PASS: scripts/healthcheck.sh exits 0
PASS: GET /health returns ok
PASS: GET /llm/status returns safe JSON
PASS: POST /projects creates project filesystem and DB row
PASS: POST /projects/{project_id}/run completes workflow
PASS: task packets are written to handoffs/
PASS: agent result files are written to handoffs/
PASS: final/final-report.md is created
PASS: GET /projects/{project_id} returns DB-backed metadata and task summary
PASS: no local Ollama is required
```

---

## 22. Completion Criteria

The v0.2 PR is complete only when:

1. v0.1 install still works.
2. PostgreSQL-backed project records are active.
3. PostgreSQL-backed task records are active.
4. default workflow run endpoint exists.
5. LangGraph workflow state is at least minimally persistent.
6. role files are loaded from harness per node.
7. task packets are written per node.
8. agent result files are written per node.
9. final report is written.
10. `/llm/status` endpoint exists.
11. runtime-inspector node and role exist.
12. tests/manual validation notes are included.
13. no autonomous self-improvement is implemented.
14. no production harness bypass is implemented.

---

## 23. Do Not Do These in v0.2

Do not implement:

* web UI
* authentication
* autonomous skill creation
* autonomous harness promotion
* production harness mutation
* live cron editing
* live systemd service editing
* sudo/root-capable workers
* Kubernetes
* multi-VM worker scheduling
* advanced semantic memory ranking
* long-term autonomous task queues
* marketplace/plugin system
* external network scraping tools
