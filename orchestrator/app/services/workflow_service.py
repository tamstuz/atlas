import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph
import yaml

from .. import llm
from ..config import settings
from ..schemas.agent_result import AgentResult
from ..schemas.task_packet import TaskPacket
from .harness_loader import load_role_bundle
from .prompt_service import assemble_prompt, load_schema_text
from .project_service import append_decision_for_project, get_project_record, update_project_status, write_project_files
from .run_service import create_agent_run, create_handoff, record_event
from .task_service import DEFAULT_WORKFLOW_ROLES, get_project_tasks, get_task_for_role, set_task_status


PLACEHOLDER_SUMMARIES = {
    "intake": "Placeholder intake result captured the original request for the workflow.",
    "analyst": "Placeholder analyst result generated because LLM endpoint is unavailable or not required.",
    "architect": "Placeholder architect result converted the request into a simple implementation plan.",
    "developer": "Placeholder developer result recorded the deterministic v0.2 implementation step.",
    "qa": "Placeholder QA result checked that required workflow artifacts were produced.",
    "final_report": "Final report generated with deterministic v0.2 content.",
}
LLM_ROLES = {"analyst", "architect", "developer", "qa", "final_report"}


class WorkflowRunState(TypedDict):
    project_id: str
    project: dict
    previous_role: str
    artifacts_created: list[str]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _step_prefix(step_number: int, role: str) -> str:
    return f"{step_number:02d}-{role}"


def _packet_for(project: dict, task: dict, role: str, loaded_files: list[str]) -> TaskPacket:
    return TaskPacket(
        project_id=str(project["id"]),
        task_id=str(task["id"]),
        role=role,
        phase=role,
        objective=f"Run the {role} workflow node for project {project['name']}.",
        input_summary=str(project["request"]),
        harness_files_loaded=loaded_files,
        allowed_scope=["Read loaded harness files", "Write project handoff artifacts", "Update task/project state"],
        forbidden_actions=[
            "Modify production harness files",
            "Create sudo/root-capable agents",
            "Perform live cron or service edits",
            "Install system packages during workflow execution",
        ],
        expected_output="Structured agent result JSON for this node.",
        definition_of_done="Task packet and agent result are written, and task status is complete.",
        created_at=_now_iso(),
    )


def _result_for(
    project_id: str,
    task_id: str,
    role: str,
    loaded_files: list[str],
    next_role: str,
    written: list[str],
    summary: str,
    llm_metadata: dict,
) -> AgentResult:
    return AgentResult(
        project_id=project_id,
        task_id=task_id,
        role=role,
        status="complete",
        summary=summary,
        artifacts_created=written,
        files_read=loaded_files,
        files_written=written,
        harness_files_loaded=loaded_files,
        next_recommended_role=next_role,
        blockers=[],
        created_at=_now_iso(),
        model=str(llm_metadata.get("model") or ""),
        provider=str(llm_metadata.get("provider") or ""),
        llm_used=bool(llm_metadata.get("llm_used")),
        fallback_used=bool(llm_metadata.get("fallback_used", True)),
        duration_ms=int(llm_metadata.get("duration_ms") or 0),
        endpoint=str(llm_metadata.get("endpoint") or ""),
        timeout_seconds=float(llm_metadata.get("timeout_seconds") or 0),
        error=str(llm_metadata.get("error") or ""),
    )


def _run_specialist(role: str, bundle: dict, packet: TaskPacket, project: dict) -> tuple[str, dict]:
    model = settings.model_for_role(role)
    metadata = {
        "provider": "ollama",
        "model": model,
        "prompt": "",
        "response": "",
        "status": "fallback",
        "duration_ms": 0,
        "endpoint": "",
        "timeout_seconds": settings.effective_llm_timeout_seconds,
        "error": "",
        "llm_used": False,
        "fallback_used": True,
    }
    if role not in LLM_ROLES:
        return PLACEHOLDER_SUMMARIES[role], metadata

    schema_path = settings.harness_dir / "schemas" / "agent-result.schema.json"
    output_schema = load_schema_text(schema_path)
    harness_files = [
        {"path": str(item["path"]), "content": str(item["content"])}
        for item in bundle["files"]
    ]
    prompt = assemble_prompt(role, harness_files, packet, str(project["request"]), output_schema)
    llm_result = llm.generate_sync(prompt, model)
    metadata.update(
        {
            "prompt": prompt,
            "response": llm_result.response,
            "status": "complete" if llm_result.ok else "fallback",
            "duration_ms": llm_result.duration_ms,
            "endpoint": llm_result.endpoint,
            "timeout_seconds": llm_result.timeout_seconds,
            "error": llm_result.error,
            "llm_used": llm_result.ok,
            "fallback_used": not llm_result.ok,
        }
    )
    if llm_result.ok and llm_result.response.strip():
        return llm_result.response.strip(), metadata
    return PLACEHOLDER_SUMMARIES[role], metadata


def _write_final_report(project: dict, tasks: list[dict], artifacts: list[str]) -> str:
    root = Path(str(project["root_path"]))
    report_path = root / "final" / "final-report.md"
    status_lines = "\n".join(f"- {task['assigned_role']}: {task['status']}" for task in tasks)
    artifact_lines = "\n".join(f"- {artifact}" for artifact in artifacts)
    report_path.write_text(
        "\n".join(
            [
                "# Final Report",
                "",
                f"Project id: {project['id']}",
                f"Project name: {project['name']}",
                "",
                "## Original Request",
                str(project["request"]),
                "",
                "## Workflow Steps Completed",
                "- intake",
                "- analyst",
                "- architect",
                "- developer",
                "- qa",
                "- final_report",
                "",
                "## Task Statuses",
                status_lines,
                "",
                "## Artifacts Created",
                artifact_lines,
                "",
                "## Known Limitations",
                "- v0.3 uses deterministic specialist output when no LLM endpoint is available.",
                "- LangGraph checkpointing is represented by persisted workflow state snapshots in PostgreSQL events.",
                "",
                "## Next Recommended Step",
                "Validate LLM-backed execution against the configured external Ollama endpoint.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return str(report_path)


def _execute_role(state: WorkflowRunState, role: str, step_number: int) -> WorkflowRunState:
    project_id = state["project_id"]
    project = state["project"]
    root = Path(str(project["root_path"]))
    task_record = get_task_for_role(project_id, role)
    if task_record is None:
        raise RuntimeError(f"Task row for role '{role}' is missing.")
    task = dict(task_record)
    set_task_status(str(task["id"]), "running")

    bundle = load_role_bundle(role)
    loaded_files = [str(item["path"]) for item in bundle["files"]]
    packet = _packet_for(project, task, role, loaded_files)
    prefix = _step_prefix(step_number, role)
    packet_path = root / "handoffs" / f"{prefix}-task-packet.yaml"
    packet_path.write_text(yaml.safe_dump(packet.model_dump(), sort_keys=False), encoding="utf-8")

    next_role = DEFAULT_WORKFLOW_ROLES[step_number] if step_number < len(DEFAULT_WORKFLOW_ROLES) else ""
    result_path = root / "handoffs" / f"{prefix}-agent-result.json"
    summary, llm_metadata = _run_specialist(role, bundle, packet, project)
    result = _result_for(
        project_id,
        str(task["id"]),
        role,
        loaded_files,
        next_role,
        [str(packet_path), str(result_path)],
        summary,
        llm_metadata,
    )
    result_path.write_text(json.dumps(result.model_dump(), indent=2) + "\n", encoding="utf-8")

    artifacts = [*state["artifacts_created"], str(packet_path), str(result_path)]
    create_agent_run(
        str(task["id"]),
        role,
        "complete",
        {**packet.model_dump(), "llm": {"prompt": llm_metadata.get("prompt"), "model": llm_metadata.get("model"), "provider": llm_metadata.get("provider")}},
        {**result.model_dump(), "llm": llm_metadata},
    )
    create_handoff(str(task["id"]), state["previous_role"], next_role or "complete", packet.model_dump())
    set_task_status(str(task["id"]), "complete")
    append_decision_for_project(project_id, f"Ran {role.replace('_', ' ')}")
    record_event(
        project_id,
        str(task["id"]),
        "workflow_state_snapshot",
        {"thread_id": project_id, "current_role": role, "artifacts": artifacts},
    )
    return {**state, "previous_role": role, "artifacts_created": artifacts}


def _build_workflow_graph():
    graph = StateGraph(WorkflowRunState)
    for step_number, role in enumerate(DEFAULT_WORKFLOW_ROLES, start=1):
        graph.add_node(role, lambda state, role=role, step_number=step_number: _execute_role(state, role, step_number))
    graph.set_entry_point("intake")
    graph.add_edge("intake", "analyst")
    graph.add_edge("analyst", "architect")
    graph.add_edge("architect", "developer")
    graph.add_edge("developer", "qa")
    graph.add_edge("qa", "final_report")
    graph.add_edge("final_report", END)
    return graph.compile()


def run_project_workflow(project_id: str) -> dict:
    project_record = get_project_record(project_id)
    if not project_record:
        raise KeyError(project_id)
    project = dict(project_record)
    root = Path(str(project["root_path"]))
    if not (root / "project-state.json").exists():
        raise FileNotFoundError(f"Project files are missing under {root}")

    project = dict(update_project_status(project_id, "running"))
    final_state = _build_workflow_graph().invoke(
        {"project_id": project_id, "project": project, "previous_role": "start", "artifacts_created": []},
        config={"configurable": {"thread_id": project_id}},
    )

    tasks = [dict(task) for task in get_project_tasks(project_id)]
    final_report_path = _write_final_report(project, tasks, final_state["artifacts_created"])
    append_decision_for_project(project_id, "Generated final report")
    project = dict(update_project_status(project_id, "complete"))
    tasks = [dict(task) for task in get_project_tasks(project_id)]
    write_project_files({**project, "current_phase": "complete"}, tasks, final_report_path)
    record_event(project_id, None, "workflow_complete", {"thread_id": project_id, "final_report_path": final_report_path})

    return {
        "project_id": project_id,
        "thread_id": project_id,
        "status": "complete",
        "workflow": DEFAULT_WORKFLOW_ROLES,
        "artifacts_created": final_state["artifacts_created"] + [final_report_path],
        "final_report_path": final_report_path,
    }
