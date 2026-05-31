from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..schemas.approval_status import DryRunValidationRequest, DryRunValidationResponse
from .approval_service import get_approval_record, update_approval_status
from .command_plan_validator import validate_command_plan
from .patch_validation_service import validate_patch
from .project_service import get_project_record
from .run_service import record_event


ROLLBACK_ITEMS = (
    "files affected",
    "backup strategy",
    "restore steps",
    "verification after rollback",
    "failure trigger",
    "owner/human approval requirement",
)


class DryRunValidationError(ValueError):
    pass


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _load_plan(approval: dict[str, object], approvals_dir: Path) -> tuple[dict[str, Any], list[str]]:
    issues: list[str] = []
    artifact_path = Path(str(approval.get("artifact_path") or ""))
    plan_json = artifact_path.with_suffix(".json") if artifact_path.name else approvals_dir / "modification-plan.json"
    if not plan_json.exists():
        fallback = approvals_dir / "modification-plan.json"
        blocked_fallback = approvals_dir / "blocked-modification-plan.json"
        plan_json = fallback if fallback.exists() else blocked_fallback
    if not plan_json.exists():
        return {}, [f"Modification plan JSON is missing under {approvals_dir}."]
    try:
        return json.loads(plan_json.read_text(encoding="utf-8")), issues
    except json.JSONDecodeError as exc:
        return {}, [f"Modification plan JSON is invalid: {exc}"]


def _plan_commands(plan: dict[str, Any]) -> list[Any]:
    commands = plan.get("proposed_commands")
    return commands if isinstance(commands, list) else []


def validate_rollback_plan(plan: dict[str, Any]) -> dict[str, object]:
    rollback = plan.get("rollback_plan")
    present = bool(rollback)
    rollback_text = json.dumps(rollback).lower() if isinstance(rollback, (dict, list)) else str(rollback or "").lower()
    missing = [item for item in ROLLBACK_ITEMS if item not in rollback_text]
    return {
        "rollback_plan_present": present,
        "rollback_plan_complete": present and not missing,
        "missing_rollback_items": missing,
    }


def _report_markdown(result: dict[str, Any]) -> str:
    issues = result["issues"] or ["None."]
    rollback = result["rollback_validation"]
    return "\n".join(
        [
            "# Dry-Run Validation Report",
            "",
            f"Project id: {result['project_id']}",
            f"Approval id: {result['approval_id']}",
            f"Status: {result['status']}",
            f"Validation mode: {result['validation_mode']}",
            "",
            "## Safety",
            f"production_modified: {result['production_modified']}",
            f"global_registries_modified: {result['global_registries_modified']}",
            f"harness_modified: {result['harness_modified']}",
            f"commands_executed: {result['command_validation']['commands_executed']}",
            f"patch_applied: {result['patch_validation']['patch_applied']}",
            "",
            "## Rollback Plan",
            f"present: {rollback['rollback_plan_present']}",
            f"complete: {rollback['rollback_plan_complete']}",
            "",
            "## Issues",
            *[f"- {issue}" for issue in issues],
            "",
            "## Next Step",
            result["next_step"],
            "",
        ]
    )


def run_dry_run_validation(project_id: str, approval_id: str, request: DryRunValidationRequest) -> DryRunValidationResponse:
    project = get_project_record(project_id)
    if not project:
        raise KeyError(project_id)
    approval = get_approval_record(approval_id)
    if not approval or str(approval["project_id"]) != project_id:
        raise KeyError(approval_id)
    if str(approval["status"]) != "approved":
        raise DryRunValidationError("Dry-run validation requires approval status approved.")

    root = Path(str(project["root_path"]))
    approvals_dir = root / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    report_path = approvals_dir / "dry-run-validation-report.md"
    result_path = approvals_dir / "dry-run-validation-result.json"
    patch_validation_path = approvals_dir / "patch-validation.json"

    record_event(
        project_id,
        None,
        "dry_run_validation_started",
        {"approval_id": approval_id, "validation_mode": request.validation_mode, "nothing_executed": True},
    )

    plan, plan_issues = _load_plan(dict(approval), approvals_dir)
    plan_blocked = str(plan.get("approval_status") or "").startswith("blocked")
    patch_validation = (
        validate_patch(approvals_dir / "dry-run.patch", root, plan_blocked=plan_blocked)
        if request.validation_mode in {"patch_only", "full_dry_run"}
        else {"status": "passed", "issues": [], "patch_applied": False, "candidate_only": True, "targets": []}
    )
    command_validation = (
        validate_command_plan(_plan_commands(plan))
        if request.validation_mode in {"plan_only", "full_dry_run"}
        else {"commands": [], "blocked_count": 0, "unknown_count": 0, "commands_executed": False}
    )
    rollback_validation = (
        validate_rollback_plan(plan)
        if request.validation_mode in {"plan_only", "full_dry_run"}
        else {"rollback_plan_present": True, "rollback_plan_complete": True, "missing_rollback_items": []}
    )

    issues = list(plan_issues)
    issues.extend(str(issue) for issue in patch_validation.get("issues", []))
    issues.extend(
        f"Blocked command: {item['command']}"
        for item in command_validation["commands"]
        if item["classification"] == "blocked"
    )
    if not rollback_validation["rollback_plan_present"]:
        issues.append("Rollback plan is missing.")
    elif not rollback_validation["rollback_plan_complete"]:
        missing = ", ".join(str(item) for item in rollback_validation["missing_rollback_items"])
        issues.append(f"Rollback plan is incomplete: {missing}.")

    status = "passed"
    if patch_validation["status"] == "blocked" or command_validation["blocked_count"] > 0:
        status = "blocked"
    elif issues or patch_validation["status"] == "failed":
        status = "failed"

    next_step = (
        "Resolve blocked dry-run validation issues before any future execution workflow."
        if status == "blocked"
        else "Resolve dry-run validation issues before approval execution is designed."
        if status == "failed"
        else "Dry-run validation passed; v0.6 still does not execute changes."
    )
    result: dict[str, Any] = {
        "project_id": project_id,
        "approval_id": approval_id,
        "status": status,
        "validation_mode": request.validation_mode,
        "validation_report_path": str(report_path),
        "validation_result_path": str(result_path),
        "patch_validation_path": str(patch_validation_path),
        "production_modified": False,
        "global_registries_modified": False,
        "harness_modified": False,
        "issues": issues,
        "next_step": next_step,
        "patch_validation": patch_validation,
        "command_validation": command_validation,
        "rollback_validation": rollback_validation,
    }

    _write_json(patch_validation_path, patch_validation)
    _write_json(result_path, result)
    report_path.write_text(_report_markdown(result), encoding="utf-8")
    update_approval_status(approval_id, str(approval["status"]), str(approval.get("reason") or ""), status, str(report_path))
    record_event(
        project_id,
        None,
        "dry_run_validation_completed",
        {
            "approval_id": approval_id,
            "validation_mode": request.validation_mode,
            "validation_status": status,
            "validation_artifact_path": str(report_path),
            "issues": issues,
            "production_modified": False,
            "global_registries_modified": False,
            "harness_modified": False,
            "nothing_executed": True,
        },
        status=status,
    )

    return DryRunValidationResponse(
        project_id=project_id,
        approval_id=approval_id,
        status=status,
        validation_report_path=str(report_path),
        patch_validation_path=str(patch_validation_path),
        production_modified=False,
        global_registries_modified=False,
        harness_modified=False,
        issues=issues,
        next_step=next_step,
    )
