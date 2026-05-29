# BUILD_DIRECTIVE_v0.1.md

# AI Lab Orchestrator — v0.1 Build Directive

## 1. Purpose

Build the first installable scaffold for **AI Lab Orchestrator**.

This repo should install a fresh Ubuntu Server 24.04 minimal VM into an AI Lab control plane that provides:

* LangGraph workflow orchestration
* FastAPI front-door API
* PostgreSQL for durable project/task/run tracking
* Qdrant for semantic memory
* Harness directory structure
* Skill directory structure
* Runtime registry structure
* Project workspace creation
* Optional external Ollama/vLLM-compatible LLM endpoint
* systemd services
* health checks
* install/uninstall scripts

This is **v0.1**. Keep it simple, reliable, and installable.

Do not build a full autonomous company yet. Build the foundation.

---

## 2. Required Design Principles

Follow these rules exactly:

1. Runtime root must be:

   ```text
   /srv/ai-lab
   ```

2. Target OS:

   ```text
   Ubuntu Server 24.04 LTS minimal install
   ```

3. Ollama must be optional and external.

   Do not require Ollama to be installed on the orchestrator VM.

4. All configurable values must come from `.env`.

5. Do not hard-code private IP addresses except in example comments.

6. LangGraph is the workflow/state-machine layer.

7. FastAPI is the HTTP/front-door API layer.

8. PostgreSQL is the durable operational database.

9. Qdrant is the vector/semantic memory database.

10. Filesystem/Git hold harness files, skills, project artifacts, and reports.

11. The installer should be idempotent where practical.

12. Agents must not directly edit `harness/prod`.

13. Candidate harness changes must go under `harness/candidate`.

14. Candidate skills must go under `skills/candidate`.

15. Do not implement autonomous self-improvement in v0.1.

16. Do not implement a web UI in v0.1.

17. Do not create root/sudo-capable autonomous agents.

---

## 3. Required Repo Structure

Create or update the repo to include this structure:

```text
ai-lab-orchestrator/
├── README.md
├── AGENTS.md
├── BUILD_DIRECTIVE_v0.1.md
├── install.sh
├── uninstall.sh
├── docker-compose.yml
├── .env.example
│
├── orchestrator/
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── db.py
│       ├── graph.py
│       ├── llm.py
│       ├── nodes/
│       │   ├── __init__.py
│       │   ├── intake.py
│       │   ├── analyst.py
│       │   ├── architect.py
│       │   ├── developer.py
│       │   ├── qa.py
│       │   └── final_report.py
│       ├── services/
│       │   ├── __init__.py
│       │   ├── harness_loader.py
│       │   ├── project_service.py
│       │   ├── task_service.py
│       │   ├── memory_service.py
│       │   └── registry_service.py
│       └── schemas/
│           ├── __init__.py
│           ├── project_state.py
│           ├── task_packet.py
│           └── agent_result.py
│
├── db/
│   ├── init.sql
│   └── migrations/
│       └── .gitkeep
│
├── harness/
│   ├── prod/
│   │   ├── 00_READ_FIRST.md
│   │   ├── workflow-rules/
│   │   │   ├── state-machine.md
│   │   │   ├── handoff-policy.md
│   │   │   ├── completion-gates.md
│   │   │   └── verification-policy.md
│   │   ├── roles/
│   │   │   ├── orchestrator.md
│   │   │   ├── analyst.md
│   │   │   ├── architect.md
│   │   │   ├── developer.md
│   │   │   ├── qa.md
│   │   │   └── final-report-writer.md
│   │   ├── runtime-control/
│   │   │   ├── absolute-path-policy.md
│   │   │   ├── discover-before-modify.md
│   │   │   ├── cron-debug-policy.md
│   │   │   └── service-debug-policy.md
│   │   ├── schemas/
│   │   │   ├── task-packet.schema.json
│   │   │   ├── agent-result.schema.json
│   │   │   └── project-state.schema.json
│   │   └── templates/
│   │       ├── task-packet.yaml
│   │       ├── handoff-packet.yaml
│   │       ├── qa-report.md
│   │       └── final-report.md
│   ├── candidate/
│   │   ├── proposals/
│   │   │   └── .gitkeep
│   │   ├── skills/
│   │   │   └── .gitkeep
│   │   ├── role-updates/
│   │   │   └── .gitkeep
│   │   └── harness-patches/
│   │       └── .gitkeep
│   └── archive/
│       └── .gitkeep
│
├── skills/
│   ├── prod/
│   │   └── .gitkeep
│   ├── candidate/
│   │   └── .gitkeep
│   └── deprecated/
│       └── .gitkeep
│
├── runtime/
│   └── registries/
│       ├── path-map.yaml
│       ├── agent-registry.yaml
│       ├── execution-map.yaml
│       ├── cron-registry.yaml
│       └── service-registry.yaml
│
├── scripts/
│   ├── healthcheck.sh
│   ├── doctor.sh
│   ├── init-db.sh
│   ├── create-project.sh
│   └── backup.sh
│
├── systemd/
│   ├── ai-lab-orchestrator.service
│   └── ai-lab-worker-runner.service
│
├── workers/
│   ├── base/
│   │   └── README.md
│   ├── developer/
│   │   └── README.md
│   ├── qa/
│   │   └── README.md
│   └── runtime-inspector/
│       └── README.md
│
└── docs/
    ├── install.md
    ├── architecture.md
    ├── operating-model.md
    ├── self-improvement.md
    └── security-model.md
```

---

## 4. Required `.env.example`

Create `.env.example` with at least:

```env
# AI Lab root paths
AI_LAB_ROOT=/srv/ai-lab
AI_LAB_HOST=0.0.0.0
AI_LAB_PORT=8088

# PostgreSQL
POSTGRES_DB=ailab
POSTGRES_USER=ailab
POSTGRES_PASSWORD=change-me
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

# Qdrant
QDRANT_URL=http://127.0.0.1:6333
QDRANT_PORT=6333

# LLM Provider
# Ollama is optional and may run on a separate dedicated server.
LLM_PROVIDER=ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://10.0.30.20:11434
DEFAULT_MODEL=gemma4:26b

# Harness
HARNESS_ACTIVE_VERSION=prod
HARNESS_DIR=/srv/ai-lab/harness/prod
SKILLS_DIR=/srv/ai-lab/skills/prod

# Runtime
PROJECTS_DIR=/srv/ai-lab/projects
RUNTIME_DIR=/srv/ai-lab/runtime
REGISTRY_DIR=/srv/ai-lab/runtime/registries
LOG_DIR=/srv/ai-lab/runtime/logs

# Service user
AI_LAB_USER=ai-lab
AI_LAB_GROUP=ai-lab
```

Do not require the example Ollama IP to be reachable during install.

---

## 5. Required Docker Compose

Create `docker-compose.yml` with:

* PostgreSQL
* Qdrant

The compose stack should use named volumes.

Required services:

```text
postgres
qdrant
```

Do not include Ollama as a required service.

Ollama may be mentioned only as an optional external endpoint.

---

## 6. Required PostgreSQL Schema

Create `db/init.sql` with tables for:

* projects
* tasks
* agent_runs
* handoffs
* approvals
* skills
* harness_versions
* improvement_proposals
* runtime_assets
* events

Minimum columns are acceptable for v0.1, but each table should include:

* primary key
* created_at
* updated_at where appropriate
* status where appropriate

The schema does not need to be perfect. It needs to support project/task/run tracking.

---

## 7. Required FastAPI App

Create a FastAPI app under:

```text
orchestrator/app/main.py
```

Minimum required endpoints:

```text
GET /health
GET /config
POST /projects
GET /projects/{project_id}
```

### `GET /health`

Returns:

```json
{
  "status": "ok",
  "service": "ai-lab-orchestrator"
}
```

### `GET /config`

Returns safe configuration only.

Do not expose secrets such as database passwords.

### `POST /projects`

Accepts:

```json
{
  "name": "test project",
  "request": "Create a hello world Python script"
}
```

Creates a new project folder under:

```text
/srv/ai-lab/projects/<project-id>/
```

With:

```text
project-state.json
task-board.json
decision-log.md
workspace/
handoffs/
qa/
final/
```

Also create a project record in PostgreSQL where practical.

### `GET /projects/{project_id}`

Returns basic project metadata and paths.

---

## 8. Required LangGraph Workflow Scaffold

Create a minimal LangGraph workflow in:

```text
orchestrator/app/graph.py
```

Required nodes:

```text
intake
analyst
architect
developer
qa
final_report
```

The v0.1 workflow can use placeholder logic. It must be structured so real LLM calls can be added later.

Workflow shape:

```text
intake
  ↓
analyst
  ↓
architect
  ↓
developer
  ↓
qa
  ↓
final_report
```

The graph should accept a state object and return updated state.

---

## 9. Required LLM Client

Create:

```text
orchestrator/app/llm.py
```

It should support an external Ollama-compatible endpoint using environment variables.

It should not fail app startup if Ollama is unreachable.

Required behavior:

* If `OLLAMA_ENABLED=false`, skip LLM calls.
* If `OLLAMA_ENABLED=true` but endpoint is unreachable, return a clear error from LLM call functions, not from app startup.
* Do not require a local Ollama install.

---

## 10. Required Harness Files

Populate the starter harness files with concise operational rules.

At minimum:

### `harness/prod/00_READ_FIRST.md`

Must explain:

* harness purpose
* production vs candidate harness
* no direct edit to production harness
* role-based loading
* absolute path requirement

### `harness/prod/workflow-rules/state-machine.md`

Must define states:

```text
INTAKE
ANALYST
ARCHITECT
DEVELOPER
QA
FINAL_REPORT
COMPLETE
BLOCKED
```

### `harness/prod/runtime-control/discover-before-modify.md`

Must define the rule:

Before modifying any cron job, service, automation, or runtime file, the agent must first identify:

1. scheduler/source
2. exact command
3. working directory
4. absolute script path
5. config files
6. logs
7. verification command

### Role files

Create concise role definitions for:

* orchestrator
* analyst
* architect
* developer
* QA
* final report writer

---

## 11. Required Runtime Registries

Create starter YAML files:

```text
runtime/registries/path-map.yaml
runtime/registries/agent-registry.yaml
runtime/registries/execution-map.yaml
runtime/registries/cron-registry.yaml
runtime/registries/service-registry.yaml
```

`path-map.yaml` must include:

```yaml
AI_LAB_ROOT: /srv/ai-lab
HARNESS_DIR: /srv/ai-lab/harness/prod
SKILLS_DIR: /srv/ai-lab/skills/prod
PROJECTS_DIR: /srv/ai-lab/projects
RUNTIME_DIR: /srv/ai-lab/runtime
REGISTRY_DIR: /srv/ai-lab/runtime/registries
LOG_DIR: /srv/ai-lab/runtime/logs
```

---

## 12. Required Install Script

Create `install.sh`.

It must:

1. Check that it is running with sufficient permissions.
2. Detect Ubuntu version and warn if unsupported.
3. Install required packages:

   * curl
   * git
   * ca-certificates
   * python3
   * python3-venv
   * python3-pip
   * docker.io or Docker CE
   * docker-compose-plugin where available
4. Create system user/group:

   * `ai-lab`
5. Create `/srv/ai-lab`.
6. Copy repo files into `/srv/ai-lab`.
7. Create Python virtual environment.
8. Install Python dependencies.
9. Create `.env` from `.env.example` if missing.
10. Start PostgreSQL and Qdrant using Docker Compose.
11. Run DB initialization.
12. Install systemd service files.
13. Start/restart the orchestrator service.
14. Run healthcheck.
15. Print next-step commands.

The script should be readable and conservative.

---

## 13. Required Uninstall Script

Create `uninstall.sh`.

It should:

* stop systemd services
* disable systemd services
* stop Docker Compose services
* ask before deleting `/srv/ai-lab`
* preserve data by default

Do not delete data without explicit confirmation.

---

## 14. Required systemd Services

Create:

```text
systemd/ai-lab-orchestrator.service
systemd/ai-lab-worker-runner.service
```

The orchestrator service should run FastAPI via uvicorn.

The worker runner can be placeholder for v0.1 but should be structured for future worker execution.

---

## 15. Required Scripts

Create:

### `scripts/healthcheck.sh`

Checks:

* `/health` endpoint
* Docker Compose services
* PostgreSQL container running
* Qdrant container running

### `scripts/doctor.sh`

Prints:

* OS version
* Docker version
* Compose version
* Python version
* AI Lab root
* orchestrator service status
* Postgres status
* Qdrant status
* configured LLM endpoint

### `scripts/init-db.sh`

Runs or verifies DB initialization.

### `scripts/create-project.sh`

Calls the API to create a project.

### `scripts/backup.sh`

Creates a basic archive backup of:

* harness
* skills
* runtime registries
* projects
* `.env` if present, but warn that it may contain secrets

---

## 16. Required Documentation

Create docs:

### `README.md`

Must include:

* project purpose
* architecture summary
* fresh install quickstart
* healthcheck commands
* first project creation test
* external Ollama configuration
* known limitations

### `docs/install.md`

Detailed install instructions.

### `docs/architecture.md`

Explain:

```text
User → Front Door API → LangGraph → Specialist Nodes → Harness/DB/Filesystem
```

### `docs/operating-model.md`

Explain:

* single point of contact
* orchestrator only orchestrates
* specialists do narrow work
* harness controls behavior
* DB tracks project/task state

### `docs/self-improvement.md`

Explain future model:

* production harness cannot be directly edited
* candidate changes are proposed
* tests and approvals are required
* no bypassing harness policy

### `docs/security-model.md`

Explain:

* no direct production harness mutation
* no default sudo agents
* absolute path policy
* discover-before-modify policy
* external LLM endpoint caution

---

## 17. Required Python Dependencies

Use a minimal dependency set.

Include in `orchestrator/requirements.txt`:

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
httpx
psycopg[binary]
langgraph
langchain-core
qdrant-client
pyyaml
```

If a dependency causes install issues, document it and keep the implementation simple.

---

## 18. Completion Criteria

The PR is complete when:

1. Repo structure exists.
2. `install.sh` exists and is executable.
3. `uninstall.sh` exists and is executable.
4. `docker-compose.yml` validates.
5. FastAPI app imports.
6. `/health` endpoint exists.
7. `/projects` endpoint creates the required folder structure.
8. Ollama is optional and external.
9. Harness/prod and harness/candidate exist.
10. Skills/prod and skills/candidate exist.
11. Runtime registries exist.
12. README explains install and first-run test.
13. No production harness bypass is implemented.
14. No full autonomous self-improvement is implemented.

---

## 19. Required PR Summary

When done, open a PR with:

* summary of what was created
* install instructions
* test commands run
* known limitations
* recommended next issues

---

## 20. Do Not Do These in v0.1

Do not implement:

* web UI
* full autonomous self-improvement
* live cron editing
* sudo-capable agents
* multi-VM scheduling
* Kubernetes
* authentication system
* advanced memory ranking
* production skill promotion automation
* direct editing of `harness/prod`
* forced local Ollama install
