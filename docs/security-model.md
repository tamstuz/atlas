# Security Model

v0.2 uses conservative governance boundaries:

- agents may not directly mutate `harness/prod`
- candidate harness changes belong under `harness/candidate`
- candidate skill changes belong under `skills/candidate`
- no sudo-capable autonomous agents are created
- runtime paths must be absolute
- cron, service, automation, and runtime changes follow discover-before-modify rules

External LLM endpoints are optional and should be treated as network dependencies. Do not place secrets in prompts or logs.

Workflow nodes load role-specific harness files and required shared rules. They may write project-local handoff artifacts and update database state, but they may not mutate `harness/prod`, create privileged agents, install packages, or make live cron/systemd edits.

v0.3 prompt assembly must include only the active node role files, required shared rules, task packet, project request, and expected output schema. It must not load unrelated harness files or authorize production harness mutation.

The runtime inspector role enforces discover-before-modify behavior by generating read-only inspection artifacts. In v0.4 it may plan read-only shell commands and, when both the request and environment allow it, execute only allowlisted read-only commands. Command execution is disabled by default.

v0.4 explicitly forbids live file modification, cron edits, systemd edits, service restarts, sudo-capable agents, self-improvement, web UI work, `harness/prod` mutation, and global runtime registry mutation. Candidate runtime registry updates may be written only under `/srv/ai-lab/projects/<project-id>/qa/candidate-runtime-registry-updates.yaml`.

v0.5 keeps those boundaries and adds approval-gated planning only. Candidate modification plans, dry-run patch placeholders, and approval requests are written only under `/srv/ai-lab/projects/<project-id>/approvals/`. v0.5 does not apply patches, execute commands, approve changes, edit cron, edit systemd, restart services, mutate `harness/prod`, or mutate global runtime registries.

v0.6 adds human approval transitions and approved dry-run validation. Approval transitions update PostgreSQL approval records and audit events only. Dry-run validation writes only `/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-report.md`, `/srv/ai-lab/projects/<project-id>/approvals/dry-run-validation-result.json`, and `/srv/ai-lab/projects/<project-id>/approvals/patch-validation.json`, plus PostgreSQL event and approval validation metadata.

The v0.6 validator blocks patch targets under `/etc`, systemd unit locations, cron locations, `/srv/ai-lab/harness/prod`, and `/srv/ai-lab/runtime/registries`. Proposed commands are classified but not executed. `sudo`, service start/stop/restart, systemd enable/disable, cron edits, package installation/removal, file deletion/move, copying into `/etc`, and Docker Compose up/down are blocked. v0.6 does not implement live execution, arbitrary shell execution, auth, web UI, self-improvement, production harness mutation, or global registry mutation.
