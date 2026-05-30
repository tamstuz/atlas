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

The runtime inspector role enforces discover-before-modify behavior by generating an inspection plan. In v0.2 it does not execute shell commands or change runtime services.
