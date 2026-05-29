# Architecture

```text
User -> Front Door API -> LangGraph -> Specialist Nodes -> Harness/DB/Filesystem
```

The FastAPI service is the front door. It exposes health, safe configuration, and project creation endpoints.

LangGraph is the workflow layer. v0.1 includes placeholder nodes for intake, analyst, architect, developer, QA, and final report.

PostgreSQL stores durable project, task, run, handoff, approval, skill, harness, runtime asset, and event records.

Qdrant is included for future semantic memory.

Filesystem and Git hold harness files, skills, project artifacts, reports, and runtime registries.
