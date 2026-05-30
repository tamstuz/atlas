# Architecture

```text
User -> Front Door API -> LangGraph -> Specialist Nodes -> Harness/DB/Filesystem
```

The FastAPI service is the front door. It exposes health, safe configuration, project creation, project read, workflow run, and LLM status endpoints.

LangGraph is the workflow layer. v0.2 runs intake, analyst, architect, developer, QA, and final report. The stable LangGraph `thread_id` is the project id.

v0.3 keeps the same workflow and adds optional LLM-backed execution for analyst, architect, developer, QA, and final report. Each eligible node assembles a prompt from the active role harness files, task packet, project request, and agent result schema. If the external Ollama-compatible endpoint is disabled or unavailable, the workflow uses deterministic fallback output.

PostgreSQL stores durable project, task, run, handoff, approval, skill, harness, runtime asset, and event records.

v0.2 persists workflow state snapshots to PostgreSQL `events`. This is a minimal checkpoint fallback, not a formal LangGraph PostgreSQL checkpoint saver.

Qdrant is included for future semantic memory.

Filesystem and Git hold harness files, skills, project artifacts, reports, and runtime registries.

Each workflow node loads only its role file and required shared rules from `HARNESS_DIR`, then writes a task packet YAML and agent result JSON under the project `handoffs/` directory. The final report is written to `final/final-report.md`.

LLM prompts, responses, model names, provider, timing, status, errors, and fallback metadata are stored in `agent_runs` JSONB fields.
