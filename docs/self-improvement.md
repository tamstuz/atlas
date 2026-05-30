# Self-Improvement

Autonomous self-improvement is not implemented in v0.2.

The future model is proposal-based:

- production harness files cannot be directly edited by agents
- candidate changes are proposed under `harness/candidate`
- candidate skills are proposed under `skills/candidate`
- tests and approvals are required before promotion
- no skill may bypass harness policy

v0.2 creates and uses workflow orchestration primitives without implementing promotion automation.

Recommended v0.3 follow-up:

- add a formal LangGraph PostgreSQL checkpoint saver if dependency review approves it
- expand manual approval workflows for candidate harness or skill promotion
- add deeper DB integration tests against PostgreSQL
