# BUILD_DIRECTIVE_v0.3.md

# AI Lab Orchestrator - v0.3 Build Directive

## 1. Purpose

Build v0.3 of **AI Lab Orchestrator**.

v0.2 created the DB-backed specialist workflow, task packets, agent result files, final reports, runtime inspector role, and optional external Ollama status endpoint.

v0.3 must make the existing specialist workflow use the configured external Ollama-compatible LLM endpoint when available, while preserving deterministic fallback behavior when the endpoint is disabled or unavailable.

This directive is linked to issue #4:

```text
Build v0.3 real LLM-backed specialist execution and Ollama integration
```

Keep this version focused. Do not build self-improvement, a web UI, or production harness mutation.

---

## 2. Core Design Rule

The orchestrator must continue to orchestrate only.

It should:

* load harness role instructions for the active specialist node
* assemble a bounded prompt for eligible specialist nodes
* call the configured external Ollama-compatible endpoint when available
* preserve deterministic fallback when the LLM is unavailable
* record prompt, response, model, timing, status, and error metadata in `agent_runs`
* write the same task packet and agent result artifacts as v0.2
* update workflow, task, and project status clearly

It should not:

* modify `harness/prod`
* autonomously create or promote skills
* bypass harness policy
* create sudo/root-capable agents
* install system packages during workflow execution
* perform live cron or systemd edits
* add a web UI
* add autonomous self-improvement
* overbuild beyond this directive

---

## 3. Required Branch / PR Behavior

Build v0.3 in a new branch.

Suggested branch name:

```text
codex/v0.3-llm-backed-specialists
```

Open a PR linked to issue #4.

The PR must include:

* summary of changes
* test commands run
* known limitations
* Ubuntu install/upgrade notes
* Ollama validation notes
* recommended v0.4 issues

Do not merge directly to main.

---

## 4. Ollama Configuration

Use the existing `.env` settings:

```text
OLLAMA_ENABLED
OLLAMA_BASE_URL
DEFAULT_MODEL
```

Add per-role model configuration using `.env` values.

Suggested names:

```text
ANALYST_MODEL
ARCHITECT_MODEL
DEVELOPER_MODEL
QA_MODEL
FINAL_REPORT_MODEL
```

If a per-role model is unset, fall back to `DEFAULT_MODEL`.

Do not hard-code local IP addresses.

Ollama remains optional and external. Do not install Ollama on the orchestrator VM.

---

## 5. `/llm/status` Update

Keep:

```text
GET /llm/status
```

Required behavior:

* return disabled status when `OLLAMA_ENABLED=false`
* validate the configured Ollama endpoint when enabled
* include configured base URL and default model
* report reachable/unreachable without crashing
* include per-role model configuration in safe JSON
* do not leak secrets

Validation should use a real configured Ollama endpoint during Ubuntu manual validation.

---

## 6. LLM-Backed Specialist Execution

The default workflow remains:

```text
intake -> analyst -> architect -> developer -> qa -> final_report
```

For v0.3, these roles should call the LLM when available:

```text
analyst
architect
developer
qa
final_report
```

`intake` may remain deterministic unless a minimal LLM call is clearly useful.

`runtime_inspector` must remain out of the default workflow.

If the LLM endpoint is disabled, unreachable, times out, or returns an invalid response, the workflow must fall back to deterministic output and continue unless a non-LLM fatal error occurs.

---

## 7. Prompt Assembly

Build prompts from:

* active harness role file
* required shared harness workflow rules
* task packet
* project request
* expected output schema

Prompt assembly should be explicit and testable.

Suggested file:

```text
orchestrator/app/services/prompt_service.py
```

Prompt requirements:

* keep prompts simple
* include only the active node's role instructions and required shared rules
* include allowed scope and forbidden actions from the task packet
* include required output schema or a concise schema summary
* tell the model to return structured content suitable for the agent result file
* do not include unrelated harness files

---

## 8. Agent Run Persistence

Store LLM execution details in PostgreSQL `agent_runs`.

At minimum, record:

```text
prompt
response
model
provider
status
duration_ms
error
fallback_used
```

Use JSONB `input` and `output` fields if practical within the existing schema.

If a schema migration is needed, add an idempotent migration under:

```text
db/migrations/
```

The migration must not drop v0.2 data.

---

## 9. Timing, Error, and Retry Handling

Add basic timing and error handling around LLM calls.

Required behavior:

* record start/end duration for each LLM attempt
* record model name used
* record provider as `ollama`
* record timeout or connection failures clearly
* use deterministic fallback after LLM failure
* update task status to `complete` when fallback succeeds
* update task/project status to `failed` only for fatal workflow errors

Add simple retry behavior only if it is small and bounded.

Do not add long-running autonomous queues.

---

## 10. Artifact Compatibility

Do not break v0.2 artifacts.

Continue writing:

```text
/srv/ai-lab/projects/<project-id>/handoffs/<step>-<role>-task-packet.yaml
/srv/ai-lab/projects/<project-id>/handoffs/<step>-<role>-agent-result.json
/srv/ai-lab/projects/<project-id>/final/final-report.md
```

Agent result files should continue to include the v0.2 required fields.

They may add fields for:

```text
model
provider
llm_used
fallback_used
duration_ms
error
```

Update schemas only as needed.

---

## 11. Documentation Updates

Update:

```text
README.md
docs/architecture.md
docs/operating-model.md
docs/install.md
docs/security-model.md
docs/v0.2-validation.md
```

At minimum, document:

* optional external Ollama behavior
* per-role model configuration
* LLM fallback behavior
* `/llm/status` expected output
* `agent_runs` prompt/response persistence
* Ubuntu validation steps with and without Ollama
* known limitations

Rename or add a v0.3 validation document if that is clearer.

---

## 12. Required Tests

Add or update lightweight tests under:

```text
orchestrator/tests/
```

Required coverage:

1. `/llm/status` disabled behavior
2. `/llm/status` unreachable behavior
3. `/llm/status` reachable behavior with mocked Ollama response
4. per-role model fallback to `DEFAULT_MODEL`
5. prompt assembly includes role instructions, task packet, project request, and schema
6. workflow completes without Ollama using deterministic fallback
7. workflow uses mocked LLM response when available
8. `agent_runs` stores prompt/response/model/status metadata where practical
9. task packet and agent result files still write correctly

Tests must not require live Ollama.

Manual Ubuntu validation must cover a live configured Ollama endpoint.

---

## 13. Required Validation Commands

Before PR is marked ready, run and report:

```bash
python -m compileall orchestrator
bash -n install.sh uninstall.sh scripts/*.sh
git diff --check
```

Also run Python tests:

```bash
cd orchestrator
python -m pytest
```

Do not claim live Ollama validation unless tested against a real configured endpoint.

---

## 14. Ubuntu Manual Validation Required Before Merge

Manual validation on Ubuntu must confirm:

```text
PASS: v0.2 install/upgrade still works
PASS: scripts/healthcheck.sh exits 0
PASS: GET /health returns ok
PASS: GET /llm/status returns disabled when Ollama is disabled
PASS: GET /llm/status returns ok against configured Ollama endpoint
PASS: POST /projects creates project filesystem and DB rows
PASS: POST /projects/{project_id}/run completes without Ollama using fallback
PASS: POST /projects/{project_id}/run completes with Ollama using real model calls
PASS: agent_runs records prompt, response, model, provider, status, timing, and fallback metadata
PASS: task packets are written to handoffs/
PASS: agent result files are written to handoffs/
PASS: final/final-report.md is created
PASS: no local Ollama install is required on the orchestrator VM
```

---

## 15. Completion Criteria

The v0.3 PR is complete only when:

1. v0.2 install and workflow behavior still work.
2. `/llm/status` validates the configured endpoint.
3. Per-role model configuration exists.
4. Analyst, architect, developer, QA, and final report can use LLM calls when available.
5. Deterministic fallback works when LLM is unavailable.
6. Prompt assembly is explicit and tested.
7. `agent_runs` records prompt, response, model, provider, status, timing, and error/fallback metadata.
8. Task packet and agent result artifacts remain compatible.
9. Workflow retry/failure status handling is clear and bounded.
10. Ubuntu validation passes with and without Ollama.
11. No autonomous self-improvement is implemented.
12. No web UI is implemented.
13. No production harness mutation is implemented.

---

## 16. Do Not Do These in v0.3

Do not implement:

* web UI
* authentication
* autonomous self-improvement
* autonomous skill creation
* autonomous harness promotion
* production harness mutation
* live cron editing
* live systemd service editing
* sudo/root-capable workers
* Kubernetes
* multi-VM worker scheduling
* marketplace/plugin system
* external network scraping tools
