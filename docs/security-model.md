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

v0.7 adds sandbox validation only. The sandbox root is `/srv/ai-lab/projects/<project-id>/sandbox/`, and source artifacts are copied into `sandbox/input/`. Candidate patches may be applied only under `sandbox/workspace/` after approval and a passed dry-run validation. Forbidden targets include `/etc`, `/usr`, `/var`, systemd locations, cron locations, `/srv/ai-lab/harness/prod`, and `/srv/ai-lab/runtime/registries`.

Sandbox command execution is disabled by default. When explicitly enabled, only narrow validation commands such as `pwd`, `ls`, `find`, `cat`, `grep`, `python3 -m py_compile`, `python3 -m compileall`, `bash -n`, and `git apply --check` may run with the sandbox as the working directory. `sudo`, system service commands, package managers, deletion/move commands, network commands, Docker execution, ownership/mode changes, production copies, web UI, auth, and arbitrary shell execution remain blocked.

v0.8 adds production change packaging only. The package generator requires an approved approval record, passed dry-run validation, and passed sandbox validation. It writes only under `/srv/ai-lab/projects/<project-id>/change-package/` and PostgreSQL `approvals`/`events`.

The exact command plan is a human-only review artifact. Commands are never passed to shell runners or execution services. Dangerous commands including `sudo`, systemd/service start-stop-restart, cron edits, package install/remove, deletion/move/copy into `/etc`, Docker execution, `chmod`, and `chown` are marked `blocked_for_agent` and `human_only`.

The final `production_change_package` approval record is not execution approval. v0.8 does not implement live production modification, production command execution, cron editing, systemd editing, service restart, sudo/root behavior, package installation, production harness mutation, global registry mutation, self-improvement, web UI, auth, arbitrary shell execution, Docker sandboxing, Kubernetes, or multi-VM scheduling.
