# Operating Model

AI Lab Orchestrator keeps a single point of contact through the front-door API.

The orchestrator only orchestrates. Specialist nodes perform narrow work in the workflow.

The harness controls behavior through role files, workflow rules, runtime-control policies, templates, and schemas.

The database tracks project, task, run, handoff, approval, runtime, and event state.

Project artifacts live under `/srv/ai-lab/projects`.
