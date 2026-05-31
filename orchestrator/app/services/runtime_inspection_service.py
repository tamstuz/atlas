import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

import yaml

from ..config import settings
from ..schemas.agent_result import AgentResult
from ..schemas.runtime_inspection import RuntimeInspectRequest, RuntimeInspectResponse
from ..schemas.task_packet import TaskPacket
from .discovery_validator import validate_discovery
from .harness_loader import load_role_bundle
from .project_service import append_decision_for_project, get_project_record
from .run_service import create_agent_run, create_handoff, record_event
from .shell_inspection_service import build_command_plan, inspect_command
from .task_service import get_task_for_role, set_task_status


RUNTIME_ROLE = "runtime_inspector"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _packet_for(project: Mapping[str, object], task: Mapping[str, object], loaded_files: list[str], request: RuntimeInspectRequest) -> TaskPacket:
    target = request.target_type
    if request.target_hint:
        target = f"{target}: {request.target_hint}"
    return TaskPacket(
        project_id=str(project["id"]),
        task_id=str(task["id"]),
        role=RUNTIME_ROLE,
        phase="runtime_inspection",
        objective="Map runtime execution paths and validate discover-before-modify readiness without modification.",
        input_summary=f"Original request: {project['request']}\nInspection target: {target}",
        harness_files_loaded=loaded_files,
        allowed_scope=[
            "Read project state",
            "Read runtime-inspector harness policy",
            "Generate project-local runtime inspection artifacts",
            "Optionally run allowlisted read-only inspection commands when explicitly enabled",
        ],
        forbidden_actions=[
            "Modify project workspace source files",
            "Modify harness/prod",
            "Mutate global runtime registries",
            "Edit cron or systemd",
            "Restart services",
            "Use sudo or root escalation",
            "Run arbitrary shell commands",
        ],
        expected_output="Runtime inspection report, evidence JSON, task packet, agent result, and candidate registry update proposal.",
        definition_of_done="Read-only inspection artifacts are written and discover-before-modify validation is recorded.",
        created_at=_now_iso(),
    )


def _initial_findings(project: Mapping[str, object], request: RuntimeInspectRequest, evidence: list[dict]) -> dict[str, object]:
    findings: dict[str, object] = {
        "scheduler_source": request.target_type if request.target_type in {"cron", "systemd", "docker"} else "",
        "exact_command": "",
        "runtime_working_directory": "",
        "absolute_script_path": "",
        "config_files": [],
        "log_files": [],
        "verification_command": "",
        "owner_service_context": "",
        "current_observed_behavior": f"Runtime inspection requested for project {project['id']}.",
        "proposed_next_step": "Complete missing discovery fields before any future modification approval workflow.",
    }
    for item in evidence:
        if item.get("status") == "complete" and item.get("command") == "pwd":
            findings["runtime_working_directory"] = str(item.get("stdout", "")).strip()
    return findings


def _result_for(
    project_id: str,
    task_id: str,
    loaded_files: list[str],
    written: list[str],
    summary: str,
    blockers: list[str],
) -> AgentResult:
    return AgentResult(
        project_id=project_id,
        task_id=task_id,
        role=RUNTIME_ROLE,
        status="complete",
        summary=summary,
        artifacts_created=written,
        files_read=loaded_files,
        files_written=written,
        harness_files_loaded=loaded_files,
        next_recommended_role="approval_gate_placeholder",
        blockers=blockers,
        created_at=_now_iso(),
        model="deterministic-runtime-inspector",
        provider="deterministic",
        llm_used=False,
        fallback_used=True,
        duration_ms=0,
        endpoint="",
        timeout_seconds=0,
        error="",
    )


def _write_report(
    path: Path,
    project: Mapping[str, object],
    request: RuntimeInspectRequest,
    command_plan: list[dict],
    evidence: list[dict],
    findings: dict[str, object],
    validation: dict[str, object],
) -> str:
    blockers = [str(item) for item in validation["missing_requirements"]]
    lines = [
        "# Runtime Inspection Report",
        "",
        f"Project id: {project['id']}",
        f"Project name: {project['name']}",
        "",
        "## Original Request",
        str(project["request"]),
        "",
        "## Inspection Target",
        f"Runtime target type: {request.target_type}",
        f"Target hint: {request.target_hint or '(none)'}",
        "",
        "## Commands Planned",
        *[f"- {item['command']}: {item['purpose']}" for item in command_plan],
        "",
        "## Commands Executed Or Skipped",
        *[f"- {item.get('command')}: {item.get('status')} - {item.get('reason', '')}" for item in evidence if item.get("kind") == "command"],
        "",
        "## Evidence Collected",
        *[f"- {item.get('kind')}: {item.get('summary', item.get('command', ''))}" for item in evidence],
        "",
        "## Execution Path Findings",
        *[f"- {key}: {value if value else '(unknown)'}" for key, value in findings.items()],
        "",
        "## Missing Discovery Requirements",
        *[f"- {item}" for item in blockers],
        "",
        "## Gate Status",
        f"safe_to_modify: {validation['safe_to_modify']}",
        f"confidence: {validation['confidence']}",
        f"reason: {validation['reason']}",
        "",
        "## Approval Gate Placeholder",
        "Future modification workflows must require explicit approval after discover-before-modify requirements are complete.",
        "",
        "## Next Recommended Step",
        "Gather missing execution-path evidence before proposing any runtime change.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return "\n".join(blockers)


def run_runtime_inspection(project_id: str, request: RuntimeInspectRequest | None = None) -> RuntimeInspectResponse:
    payload = request or RuntimeInspectRequest()
    project_record = get_project_record(project_id)
    if not project_record:
        raise KeyError(project_id)
    project = dict(project_record)
    root = Path(str(project["root_path"]))
    if not (root / "project-state.json").exists():
        raise FileNotFoundError(f"Project files are missing under {root}")

    task_record = get_task_for_role(project_id, RUNTIME_ROLE)
    if task_record is None:
        raise RuntimeError("Task row for role 'runtime_inspector' is missing.")
    task = dict(task_record)
    handoffs_dir = root / "handoffs"
    qa_dir = root / "qa"
    handoffs_dir.mkdir(parents=True, exist_ok=True)
    qa_dir.mkdir(parents=True, exist_ok=True)

    set_task_status(str(task["id"]), "running")
    record_event(project_id, str(task["id"]), "runtime_inspection_started", payload.model_dump())

    try:
        bundle = load_role_bundle(RUNTIME_ROLE)
        loaded_files = [str(item["path"]) for item in bundle["files"]]
        packet = _packet_for(project, task, loaded_files, payload)
        packet_path = handoffs_dir / "runtime-inspector-task-packet.yaml"
        packet_path.write_text(yaml.safe_dump(packet.model_dump(), sort_keys=False), encoding="utf-8")

        planned = build_command_plan(payload.target_type, payload.target_hint)
        command_plan = [{"command": " ".join(item.args), "args": item.args, "purpose": item.purpose} for item in planned]
        commands_enabled = payload.allow_read_only_commands and settings.runtime_inspection_commands_enabled
        command_evidence = [
            {
                "kind": "command",
                "purpose": command.purpose,
                **inspect_command(command.args, commands_enabled=commands_enabled),
            }
            for command in planned
        ]
        evidence = [
            {"kind": "harness", "summary": "Runtime inspector policy files loaded.", "files": loaded_files},
            {"kind": "project", "summary": "Project state loaded.", "root_path": str(root)},
            *command_evidence,
        ]
        findings = _initial_findings(project, payload, command_evidence)
        validation = validate_discovery(findings)
        blockers = [str(item) for item in validation["missing_requirements"]]

        evidence_path = qa_dir / "runtime-inspection-evidence.json"
        _write_json(
            evidence_path,
            {
                "project_id": project_id,
                "request": payload.model_dump(),
                "command_execution_enabled": commands_enabled,
                "command_plan": command_plan,
                "evidence": evidence,
                "findings": findings,
                "validation": validation,
            },
        )
        candidate_registry_path = qa_dir / "candidate-runtime-registry-updates.yaml"
        candidate_registry_path.write_text(
            yaml.safe_dump(
                {
                    "project_id": project_id,
                    "status": "candidate_only",
                    "applied": False,
                    "reason": "v0.4 does not mutate global runtime registries.",
                    "proposed_updates": [],
                    "evidence_path": str(evidence_path),
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        report_path = qa_dir / "runtime-inspection-report.md"
        _write_report(report_path, project, payload, command_plan, evidence, findings, validation)

        summary = "Runtime inspection completed in read-only mode; modification remains blocked pending complete discovery."
        result_path = handoffs_dir / "runtime-inspector-agent-result.json"
        written = [str(packet_path), str(result_path), str(report_path), str(evidence_path), str(candidate_registry_path)]
        result = _result_for(project_id, str(task["id"]), loaded_files, written, summary, blockers)
        _write_json(result_path, result.model_dump())
        agent_output = {
            **result.model_dump(),
            "safe_to_modify": bool(validation["safe_to_modify"]),
            "blockers": blockers,
            "evidence_path": str(evidence_path),
            "evidence_count": len(evidence),
            "evidence_summary": [str(item.get("summary") or item.get("command") or item.get("kind")) for item in evidence],
            "validation": validation,
        }
        create_agent_run(
            str(task["id"]),
            RUNTIME_ROLE,
            "complete",
            {**packet.model_dump(), "request": payload.model_dump(), "command_plan": command_plan},
            agent_output,
        )
        create_handoff(str(task["id"]), "runtime_inspection_request", "approval_gate_placeholder", packet.model_dump())
        set_task_status(str(task["id"]), "complete")
        append_decision_for_project(project_id, "Ran read-only runtime inspection")
        record_event(
            project_id,
            str(task["id"]),
            "runtime_inspection_completed",
            {"report_path": str(report_path), "safe_to_modify": validation["safe_to_modify"]},
        )

        return RuntimeInspectResponse(
            project_id=project_id,
            status="complete",
            runtime_inspection_report_path=str(report_path),
            task_packet_path=str(packet_path),
            agent_result_path=str(result_path),
            inspection_summary=summary,
            blockers=blockers,
            evidence=evidence,
            safe_to_modify=bool(validation["safe_to_modify"]),
        )
    except Exception as exc:
        set_task_status(str(task["id"]), "failed")
        record_event(project_id, str(task["id"]), "runtime_inspection_failed", {"error": str(exc)}, status="failed")
        raise
