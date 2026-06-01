from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .. import db
from ..schemas.change_package import (
    ChangePackageRead,
    ChangePackageRequest,
    ChangePackageResponse,
    ChangePackagesResponse,
)
from .approval_service import create_approval_record, get_approval_record
from .command_classification_service import classify_human_commands
from .human_checklist_service import (
    EXECUTION_ITEMS,
    POSTCHANGE_ITEMS,
    PREFLIGHT_ITEMS,
    ROLLBACK_ITEMS,
    markdown_checklist,
)
from .project_service import get_project_record
from .run_service import record_event


FINAL_APPROVAL_TYPE = "production_change_package"
SOURCE_ARTIFACT_NAMES = (
    "modification-plan.md",
    "modification-plan.json",
    "dry-run.patch",
    "dry-run-validation-result.json",
    "patch-validation.json",
    "sandbox-run-result.json",
    "sandbox-run-report.md",
    "sandbox-file-manifest.json",
    "sandbox-command-log.json",
)


class ChangePackageError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _load_json(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"Required artifact is missing: {path}"]
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except json.JSONDecodeError as exc:
        return {}, [f"Artifact is invalid JSON: {path.name}: {exc}"]


def _ensure_project_child(project_root: Path, child: Path) -> None:
    root = project_root.resolve()
    resolved = child.resolve()
    if root != resolved and root not in resolved.parents:
        raise ChangePackageError(f"Path escapes project folder: {child}")


def _source_paths(approval: dict[str, object], project_root: Path) -> dict[str, Path]:
    approvals_dir = project_root / "approvals"
    sandbox_dir = project_root / "sandbox"
    plan_md = Path(str(approval.get("artifact_path") or ""))
    if not plan_md.exists():
        plan_md = approvals_dir / "modification-plan.md"
    plan_json = plan_md.with_suffix(".json")
    if not plan_json.exists():
        plan_json = approvals_dir / "modification-plan.json"
    return {
        "modification-plan.md": plan_md,
        "modification-plan.json": plan_json,
        "dry-run.patch": approvals_dir / "dry-run.patch",
        "dry-run-validation-result.json": approvals_dir / "dry-run-validation-result.json",
        "patch-validation.json": approvals_dir / "patch-validation.json",
        "sandbox-run-result.json": sandbox_dir / "sandbox-run-result.json",
        "sandbox-run-report.md": sandbox_dir / "sandbox-run-report.md",
        "sandbox-file-manifest.json": sandbox_dir / "sandbox-file-manifest.json",
        "sandbox-command-log.json": sandbox_dir / "sandbox-command-log.json",
    }


def _copy_source_artifacts(project_root: Path, package_dir: Path, sources: dict[str, Path]) -> tuple[dict[str, str], list[str]]:
    source_dir = package_dir / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    issues: list[str] = []
    for name in SOURCE_ARTIFACT_NAMES:
        source = sources[name]
        if not source.exists():
            continue
        if source.is_symlink():
            issues.append(f"Source artifact must not be a symlink: {source}")
            continue
        _ensure_project_child(project_root, source)
        destination = source_dir / name
        shutil.copy2(source, destination)
        copied[name] = str(destination)
    return copied, issues


def _plan_commands(plan: dict[str, Any]) -> list[Any]:
    commands = plan.get("proposed_commands")
    return commands if isinstance(commands, list) else []


def _list_text(items: list[Any] | tuple[Any, ...]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- None recorded."]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _production_package_markdown(payload: dict[str, Any]) -> str:
    command_lines = [
        f"- `{command['command']}`: {', '.join(command['classification'])}; {command['warning']}"
        for command in payload["command_classification"]["commands"]
    ] or ["- None recorded."]
    return "\n".join(
        [
            "# Production Change Package",
            "",
            f"Project id: {payload['project_id']}",
            f"Project name: {payload['project_name']}",
            f"Approval id: {payload['approval_id']}",
            f"Change request: {payload['change_request']}",
            f"Change window: {payload['change_window'] or '(not specified)'}",
            f"Operator: {payload['operator'] or '(not specified)'}",
            f"Target type: {payload['target_type'] or '(not specified)'}",
            f"Target hint: {payload['target_hint'] or '(not specified)'}",
            "",
            "## Runtime Inspection Summary",
            payload["runtime_inspection_summary"],
            "",
            "## Dry-Run Validation Summary",
            payload["dry_run_validation_summary"],
            "",
            "## Sandbox Validation Summary",
            payload["sandbox_validation_summary"],
            "",
            "## Evidence-Backed Facts",
            *_list_text(payload["evidence_backed_facts"]),
            "",
            "## Inferences",
            *_list_text(payload["inferences"]),
            "",
            "## Unknowns",
            *_list_text(payload["unknowns"]),
            "",
            "## Blocked Items",
            *_list_text(payload["blocked_items"]),
            "",
            "## Human-Required Steps",
            *_list_text(payload["human_required_steps"]),
            "",
            "## Risk Rating",
            payload["risk_rating"],
            "",
            "## Production Impact",
            payload["production_impact"],
            "",
            "## Exact Files Proposed For Change",
            *_list_text(payload["exact_files_proposed_for_change"]),
            "",
            "## Exact Commands Proposed For Human Execution",
            *command_lines,
            "",
            "## Pre-Flight Checklist",
            *[f"- [ ] {item}" for item in PREFLIGHT_ITEMS],
            "",
            "## Execution Checklist",
            *[f"- [ ] {item}" for item in EXECUTION_ITEMS],
            "",
            "## Rollback Checklist",
            *[f"- [ ] {item}" for item in ROLLBACK_ITEMS],
            "",
            "## Post-Change Checklist",
            *[f"- [ ] {item}" for item in POSTCHANGE_ITEMS],
            "",
            "## Final Approval Status",
            "pending review of this production change package",
            "",
            "## Execution Statement",
            "Nothing was executed. v0.8 generated a human-reviewed package only.",
            "",
        ]
    )


def _command_plan_markdown(classification: dict[str, Any]) -> str:
    lines = [
        "# Exact Command Plan",
        "",
        "Human-only review document. v0.8 did not execute these commands and does not call command execution services.",
        "",
    ]
    for index, command in enumerate(classification["commands"], start=1):
        lines.extend(
            [
                f"## Command {index}",
                "",
                f"```bash\n{command['command']}\n```",
                f"Classification: {', '.join(command['classification'])}",
                f"blocked_for_agent: {command['blocked_for_agent']}",
                f"human_only: {command['human_only']}",
                f"Warning: {command['warning']}",
                "",
            ]
        )
    if not classification["commands"]:
        lines.append("No commands were proposed.")
        lines.append("")
    return "\n".join(lines)


def _blocked_response(project_id: str, approval_id: str, issues: list[str]) -> ChangePackageResponse:
    record_event(
        project_id,
        None,
        "change_package_blocked",
        {"approval_id": approval_id, "issues": issues, "nothing_executed": True},
        status="blocked",
    )
    return ChangePackageResponse(
        project_id=project_id,
        approval_id=approval_id,
        status="blocked",
        issues=issues,
        next_step="Resolve prerequisite issues before generating a production change package.",
    )


def generate_change_package(project_id: str, approval_id: str, request: ChangePackageRequest) -> ChangePackageResponse:
    project_record = get_project_record(project_id)
    if not project_record:
        raise KeyError(project_id)
    approval = get_approval_record(approval_id)
    if not approval or str(approval["project_id"]) != project_id:
        raise KeyError(approval_id)

    project = dict(project_record)
    approval_dict = dict(approval)
    project_root = Path(str(project["root_path"]))
    package_dir = project_root / "change-package"
    _ensure_project_child(project_root, package_dir)

    record_event(
        project_id,
        None,
        "change_package_started",
        {"approval_id": approval_id, "change_window": request.change_window, "operator": request.operator, "nothing_executed": True},
    )

    if str(approval["status"]) != "approved":
        return _blocked_response(project_id, approval_id, ["Change package requires approval status approved."])

    sources = _source_paths(approval_dict, project_root)
    plan, plan_issues = _load_json(sources["modification-plan.json"])
    dry_run, dry_issues = _load_json(sources["dry-run-validation-result.json"])
    sandbox, sandbox_issues = _load_json(sources["sandbox-run-result.json"])
    issues = plan_issues + dry_issues + sandbox_issues
    if dry_run and dry_run.get("status") != "passed":
        issues.append("Change package requires prior dry-run validation status passed.")
    if sandbox and sandbox.get("status") != "passed":
        issues.append("Change package requires prior sandbox validation status passed.")
    if issues:
        return _blocked_response(project_id, approval_id, issues)

    package_dir.mkdir(parents=True, exist_ok=True)
    if package_dir.is_symlink():
        raise ChangePackageError(f"Change package path must not be a symlink: {package_dir}")
    copied, copy_issues = _copy_source_artifacts(project_root, package_dir, sources)
    record_event(project_id, None, "change_package_sources_loaded", {"approval_id": approval_id, "copied": copied, "issues": copy_issues})
    if copy_issues:
        return _blocked_response(project_id, approval_id, copy_issues)

    command_classification = classify_human_commands(_plan_commands(plan))
    metadata = {
        "project_id": project_id,
        "approval_id": approval_id,
        "change_window": request.change_window,
        "operator": request.operator,
    }
    package_md_path = package_dir / "production-change-package.md"
    package_json_path = package_dir / "production-change-package.json"
    execution_path = package_dir / "human-execution-checklist.md"
    command_plan_path = package_dir / "exact-command-plan.md"
    rollback_path = package_dir / "rollback-checklist.md"
    preflight_path = package_dir / "preflight-checklist.md"
    postchange_path = package_dir / "postchange-checklist.md"
    final_request_path = package_dir / "final-approval-request.json"
    manifest_path = package_dir / "source-artifact-manifest.json"

    payload: dict[str, Any] = {
        "project_id": project_id,
        "project_name": str(project["name"]),
        "approval_id": approval_id,
        "change_request": str(plan.get("change_request") or project.get("request") or ""),
        "change_window": request.change_window,
        "operator": request.operator,
        "notes": request.notes,
        "target_type": str(plan.get("target_type") or ""),
        "target_hint": str(plan.get("target_hint") or ""),
        "runtime_inspection_summary": str(plan.get("runtime_inspection_source") or "Runtime inspection evidence referenced by modification plan."),
        "dry_run_validation_summary": f"Dry-run validation status: {dry_run.get('status')}.",
        "sandbox_validation_summary": f"Sandbox validation status: {sandbox.get('status')}.",
        "evidence_backed_facts": _as_list(plan.get("evidence_backed_facts")),
        "inferences": _as_list(plan.get("inferences")),
        "unknowns": _as_list(plan.get("unknowns")),
        "blocked_items": _as_list(plan.get("blocked_items")),
        "human_required_steps": list(PREFLIGHT_ITEMS + EXECUTION_ITEMS + ROLLBACK_ITEMS + POSTCHANGE_ITEMS),
        "risk_rating": str(plan.get("risk_rating") or "medium"),
        "production_impact": "Production impact is proposed for human review only; no production changes were executed.",
        "exact_files_proposed_for_change": _as_list(plan.get("proposed_files_to_change")),
        "command_classification": command_classification,
        "source_artifacts": copied,
        "production_modified": False,
        "global_registries_modified": False,
        "harness_modified": False,
        "nothing_executed": True,
        "created_at": _now_iso(),
    }

    package_md_path.write_text(_production_package_markdown(payload), encoding="utf-8")
    _write_json(package_json_path, payload)
    execution_path.write_text(markdown_checklist("Human Execution Checklist", EXECUTION_ITEMS, metadata), encoding="utf-8")
    command_plan_path.write_text(_command_plan_markdown(command_classification), encoding="utf-8")
    rollback_path.write_text(markdown_checklist("Rollback Checklist", ROLLBACK_ITEMS, metadata), encoding="utf-8")
    preflight_path.write_text(markdown_checklist("Pre-Flight Verification Checklist", PREFLIGHT_ITEMS, metadata), encoding="utf-8")
    postchange_path.write_text(markdown_checklist("Post-Change Verification Checklist", POSTCHANGE_ITEMS, metadata), encoding="utf-8")
    _write_json(manifest_path, {"source_artifacts": copied, "required_when_present": list(SOURCE_ARTIFACT_NAMES)})

    final_approval = create_approval_record(
        project_id,
        FINAL_APPROVAL_TYPE,
        "pending",
        str(package_md_path),
        requested_by=request.operator or "system",
        reason="Production change package awaits final human review.",
    )
    final_approval_id = str(final_approval["id"])
    _write_json(
        final_request_path,
        {
            "project_id": project_id,
            "approval_id": approval_id,
            "final_approval_id": final_approval_id,
            "approval_type": FINAL_APPROVAL_TYPE,
            "status": "pending",
            "artifact_path": str(package_md_path),
            "execution_approval": False,
            "created_at": _now_iso(),
        },
    )
    record_event(project_id, None, "final_approval_created", {"approval_id": approval_id, "final_approval_id": final_approval_id})
    record_event(
        project_id,
        None,
        "change_package_generated",
        {
            "approval_id": approval_id,
            "final_approval_id": final_approval_id,
            "artifact_path": str(package_md_path),
            "production_modified": False,
            "global_registries_modified": False,
            "harness_modified": False,
            "nothing_executed": True,
        },
        status="packaged",
    )

    return ChangePackageResponse(
        project_id=project_id,
        approval_id=approval_id,
        status="packaged",
        change_package_path=str(package_md_path),
        execution_checklist_path=str(execution_path),
        rollback_checklist_path=str(rollback_path),
        preflight_checklist_path=str(preflight_path),
        postchange_checklist_path=str(postchange_path),
        final_approval_id=final_approval_id,
        production_modified=False,
        global_registries_modified=False,
        harness_modified=False,
        issues=[],
        next_step="Human must review the production change package and final approval record; v0.8 does not execute production changes.",
    )


def list_change_packages(project_id: str) -> ChangePackagesResponse:
    project = get_project_record(project_id)
    if not project:
        raise KeyError(project_id)
    rows = db.fetch_all(
        """
        SELECT a.id,
               a.project_id,
               a.approval_type,
               a.status,
               a.artifact_path,
               a.created_at,
               a.updated_at,
               e.payload->>'approval_id' AS source_approval_id
        FROM approvals a
        LEFT JOIN events e
          ON e.project_id = a.project_id
         AND e.event_type = 'change_package_generated'
         AND e.payload->>'final_approval_id' = a.id::text
        WHERE a.project_id = %s AND a.approval_type = %s
        ORDER BY a.created_at ASC
        """,
        (project_id, FINAL_APPROVAL_TYPE),
    )
    packages = [
        ChangePackageRead(
            approval_id=str(row.get("source_approval_id") or ""),
            final_approval_id=str(row["id"]),
            status=str(row["status"]),
            artifact_path=str(row.get("artifact_path") or ""),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )
        for row in rows
    ]
    return ChangePackagesResponse(project_id=project_id, change_packages=packages)
