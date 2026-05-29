# AGENTS.md

## Project Name

AI Lab Orchestrator

## Project Goal

Build a repo-based installer that turns a fresh Ubuntu Server minimum install into an AI Lab control plane.

The system installs and configures:

- LangGraph workflow orchestration
- Hermes-compatible front-door/worker integration layer
- Harness system
- PostgreSQL
- Qdrant
- FastAPI API service
- Worker runner
- Runtime registries
- Project workspace structure
- Optional external Ollama/vLLM endpoint

The local LLM server is external and optional. Do not require Ollama to be installed on the orchestrator VM.

## Hard Requirements

- Runtime root must be `/srv/ai-lab`.
- Use Ubuntu Server 24.04 LTS as the default supported target.
- Use `.env` for all configurable settings.
- Do not hard-code local IP addresses.
- Ollama must remain optional and external.
- Use PostgreSQL for durable project/task/run state.
- Use Qdrant for semantic memory.
- Use filesystem/Git for harness, skills, and project artifacts.
- Use LangGraph for workflow routing/state machine behavior.
- Use FastAPI for the front-door API.
- Use Docker Compose for PostgreSQL and Qdrant.
- Install systemd services for the orchestrator and worker runner.
- The installer must be idempotent where practical.

## Safety / Governance Rules

- Agents may not edit `harness/prod` directly.
- Candidate harness changes must go under `harness/candidate`.
- Candidate skills must go under `skills/candidate`.
- Production skill or harness promotion requires an approval workflow.
- No skill may bypass harness policy.
- All runtime paths must be absolute.
- Cron/service modification workflows must follow discover-before-modify rules.
- Do not grant sudo/root behavior to agents by default.
- Do not install unrelated packages.
- Do not create background jobs unless registered in the runtime registry.

## Expected Repo Structure

```text
ai-lab-orchestrator/
├── README.md
├── AGENTS.md
├── install.sh
├── uninstall.sh
├── docker-compose.yml
├── .env.example
├── orchestrator/
├── db/
├── harness/
├── skills/
├── runtime/
├── scripts/
├── systemd/
├── workers/
└── docs/
