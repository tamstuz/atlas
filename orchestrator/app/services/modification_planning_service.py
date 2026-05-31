import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from ..schemas.modification_plan import ApprovalRead, ApprovalsResponse, ModificationPlanRequest, ModificationPlanResponse
from .approval_service import create_approval_record, get_project_approvals
from .project_service import get_project_record
from .run_service import create_agent_run, record_event


APPROVAL_TYPE = "modification_plan"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _load_runtime_evidence(root: Path) -> tuple[dict, list[str]]:
    evidence_path = root / "qa" / "runtime-inspection-evidence.json"
    if not evidence_path.exists():
        return {}, ["Runtime inspection evidence is missing."]
    try:
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, [f"Runtime inspection evidence is invalid JSON: {exc}"]
    validation = evidence.get("validation") if isinstance(evidence.get("validation"), dict) else {}
    missing = validation.get("missing_requirements") if isinstance(validation.get("missing_requirements"), list) else []
    return evidence, [str(item) for item in missing]


def _safe_to_modify(evidence: dict) -> bool:
    validation = evidence.get("validation") if isinstance(evidence.get("validation"), dict) else {}
    return bool(validation.get("safe_to_modify"))


def _plan_payload(
    project: Mapping[str, object],
    request: ModificationPlanRequest,
    evidence: dict,
    safe_to_modify: bool,
    blockers: list[str],
    status: str,
    approval_id: str = "",
) -> dict[str, object]:
    evidence_path = Path(str(project["root_path"])) / "qa" / "runtime-inspection-evidence.json"
    return {
        "project_id": str(project["id"]),
        "project_name": str(project["name"]),
        "change_request": request.change_request,
        "target_type": request.target_type,
        "target_hint": request.target_hint,
        "runtime_inspection_source": str(evidence_path) if evidence else "",
        "safe_to_modify": safe_to_modify,
        "missing_discovery_requirements": blockers,
        "proposed_files_to_change": [],
        "proposed_commands": [],
        "proposed_validation_steps": [
            "Review runtime inspection evidence.",
            "Review this candidate modification plan.",
            "Do not execute changes in v0.5.",
        ],
        "rollback_plan": "No rollback required because v0.5 does not execute or apply modifications.",
        "risk_rating": "high" if blockers else "medium",
        "approval_status": status,
        "approval_id": approval_id,
        "nothing_executed": True,
        "evidence_backed_facts": [
            f"Runtime inspection safe_to_modify={safe_to_modify}.",
            f"Runtime inspection blockers recorded: {len(blockers)}.",
        ],
        "inferences": ["A future approval-execution workflow would need explicit human approval."],
        "unknowns": blockers,
        "blocked_items": blockers,
    }


def _write_markdown_plan(path: Path, payload: dict[str, object]) -> None:
    blockers = payload["blocked_items"] if isinstance(payload["blocked_items"], list) else []
    lines = [
        "# Candidate Modification Plan",
        "",
        f"Project id: {payload['project_id']}",
        f"Project name: {payload['project_name']}",
        f"Approval status: {payload['approval_status']}",
        f"Approval id: {payload.get('approval_id') or '(not created yet)'}",
        "",
        "## Change Request",
        str(payload["change_request"]),
        "",
        "## Target",
        f"Type: {payload['target_type']}",
        f"Hint: {payload['target_hint'] or '(none)'}",
        "",
        "## Runtime Inspection",
        f"Source: {payload['runtime_inspection_source'] or '(missing)'}",
        f"safe_to_modify: {payload['safe_to_modify']}",
        "",
        "## Evidence-Backed Facts",
        *[f"- {item}" for item in payload["evidence_backed_facts"]],
        "",
        "## Inferences",
        *[f"- {item}" for item in payload["inferences"]],
        "",
        "## Unknowns",
        *([f"- {item}" for item in payload["unknowns"]] or ["- None recorded."]),
        "",
        "## Blocked Items",
        *([f"- {item}" for item in blockers] or ["- None recorded."]),
        "",
        "## Proposed Files To Change",
        "- None. v0.5 does not execute or apply changes.",
        "",
        "## Proposed Commands",
        "- None. v0.5 does not execute commands.",
        "",
        "## Proposed Validation Steps",
        *[f"- {item}" for item in payload["proposed_validation_steps"]],
        "",
        "## Rollback Plan",
        str(payload["rollback_plan"]),
        "",
        "## Risk Rating",
        str(payload["risk_rating"]),
        "",
        "## Execution Statement",
        "Nothing was executed. This is a project-local candidate plan only.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_dry_run_patch(path: Path, blocked: bool) -> None:
    reason = "blocked by incomplete runtime inspection evidence" if blocked else "candidate plan requires human approval before any future execution"
    path.write_text(
        "\n".join(
            [
                "# Candidate dry-run patch only.",
                f"# No patch was applied; {reason}.",
                "# v0.5 must not target harness/prod, global runtime registries, or system files for live mutation.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def create_modification_plan(project_id: str, request: ModificationPlanRequest) -> ModificationPlanResponse:
    project_record = get_project_record(project_id)
    if not project_record:
        raise KeyError(project_id)
    project = dict(project_record)
    root = Path(str(project["root_path"]))
    if not (root / "project-state.json").exists():
        raise FileNotFoundError(f"Project files are missing under {root}")

    approvals_dir = root / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    record_event(project_id, None, "modification_planning_started", request.model_dump())

    evidence, blockers = _load_runtime_evidence(root)
    safe_to_modify = _safe_to_modify(evidence)
    blocked = not evidence or ((not safe_to_modify or bool(blockers)) and not request.allow_plan_with_blockers)
    status = "blocked" if blocked else "pending_approval"
    base_name = "blocked-modification-plan" if blocked else "modification-plan"
    plan_md = approvals_dir / f"{base_name}.md"
    plan_json = approvals_dir / f"{base_name}.json"
    dry_run_patch = approvals_dir / "dry-run.patch"
    approval_request = approvals_dir / "approval-request.json"
    next_step = (
        "Complete runtime inspection blockers before requesting a modification plan."
        if blocked
        else "Human approval is required before any future execution workflow."
    )

    payload = _plan_payload(project, request, evidence, safe_to_modify, blockers, status)
    _write_markdown_plan(plan_md, payload)
    _write_json(plan_json, payload)
    _write_dry_run_patch(dry_run_patch, blocked)

    approval = create_approval_record(
        project_id,
        APPROVAL_TYPE,
        "blocked" if blocked else "pending",
        str(plan_md),
        requested_by="system",
        reason="; ".join(blockers) if blockers else "Candidate modification plan requires human approval.",
    )
    payload["approval_id"] = str(approval["id"])
    _write_markdown_plan(plan_md, payload)
    _write_json(plan_json, payload)
    _write_json(
        approval_request,
        {
            "project_id": project_id,
            "approval_id": str(approval["id"]),
            "approval_type": APPROVAL_TYPE,
            "status": str(approval["status"]),
            "artifact_path": str(plan_md),
            "approval_required": True,
            "nothing_executed": True,
            "created_at": _now_iso(),
        },
    )
    record_event(
        project_id,
        None,
        "modification_planning_blocked" if blocked else "modification_planning_pending_approval",
        {
            "approval_id": str(approval["id"]),
            "plan_path": str(plan_md),
            "safe_to_modify": safe_to_modify,
            "blockers": blockers,
            "nothing_executed": True,
        },
    )
    create_agent_run(
        None,
        "modification_planner",
        status,
        {"request": request.model_dump(), "runtime_evidence_path": str(root / "qa" / "runtime-inspection-evidence.json")},
        {
            "approval_id": str(approval["id"]),
            "safe_to_modify": safe_to_modify,
            "blockers": blockers,
            "plan_path": str(plan_md),
            "dry_run_patch_path": str(dry_run_patch),
            "approval_required": True,
            "nothing_executed": True,
            "fallback_used": True,
            "provider": "deterministic",
            "model": "deterministic-modification-planner",
        },
    )

    return ModificationPlanResponse(
        project_id=project_id,
        status=status,
        approval_id=str(approval["id"]),
        safe_to_modify=safe_to_modify,
        plan_path=str(plan_md),
        dry_run_patch_path=str(dry_run_patch),
        approval_required=True,
        blockers=blockers,
        next_step=next_step,
    )


def list_project_approvals(project_id: str) -> ApprovalsResponse:
    project_record = get_project_record(project_id)
    if not project_record:
        raise KeyError(project_id)
    approvals = [
        ApprovalRead(
            approval_id=str(row["id"]),
            approval_type=str(row.get("approval_type") or row.get("action") or ""),
            status=str(row["status"]),
            artifact_path=str(row.get("artifact_path") or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
        for row in get_project_approvals(project_id)
    ]
    return ApprovalsResponse(project_id=project_id, approvals=approvals)
