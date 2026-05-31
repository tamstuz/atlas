# Operating Model

AI Lab Orchestrator keeps a single point of contact through the front-door API.

The orchestrator only orchestrates. Specialist nodes perform narrow work in the workflow and write structured handoff artifacts.

The harness controls behavior through role files, workflow rules, runtime-control policies, templates, and schemas.

The database tracks project, task, run, handoff, approval, runtime, and event state.

Project artifacts live under `/srv/ai-lab/projects`.

v0.2 project creation creates a PostgreSQL project row, initial task rows for intake, analyst, architect, developer, QA, final report, and runtime inspector, plus the project filesystem.

The default workflow is:

```text
intake -> analyst -> architect -> developer -> qa -> final_report
```

The runtime inspector role exists but does not run by default. It produces an inspection plan based on runtime-control harness policy and does not perform live cron or service edits.

v0.3 uses the configured external Ollama-compatible endpoint for analyst, architect, developer, QA, and final report when available. The orchestrator records the prompt, response, model, provider, timing, status, and fallback metadata in `agent_runs`.

If Ollama is disabled or unreachable, the same workflow completes with deterministic fallback output.
