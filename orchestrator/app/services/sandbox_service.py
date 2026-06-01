from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ..schemas.sandbox_run import SandboxRunRequest, SandboxRunResponse
from .approval_service import get_approval_record
from .project_service import get_project_record
from .run_service import record_event
from .sandbox_command_service import validate_and_maybe_run_commands
from .sandbox_patch_service import apply_patch_in_sandbox


class SandboxRunError(ValueError):
    pass


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SandboxRunError(f"{path.name} is invalid JSON: {exc}") from exc


def _ensure_project_child(project_root: Path, child: Path) -> None:
    root = project_root.resolve()
    resolved = child.resolve()
    if root != resolved and root not in resolved.parents:
        raise SandboxRunError(f"Path escapes project folder: {child}")


def _prepare_sandbox(project_root: Path) -> dict[str, Path]:
    sandbox = project_root / "sandbox"
    _ensure_project_child(project_root, sandbox)
    if sandbox.exists():
        if sandbox.is_symlink():
            raise SandboxRunError(f"Sandbox path must not be a symlink: {sandbox}")
        shutil.rmtree(sandbox)
    paths = {
        "sandbox": sandbox,
        "input": sandbox / "input",
        "workspace": sandbox / "workspace",
        "output": sandbox / "output",
        "logs": sandbox / "logs",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise SandboxRunError(f"Sandbox path must not be a symlink: {path}")
    return paths


def _source_plan_paths(approval: dict[str, object], approvals_dir: Path) -> tuple[Path, Path]:
    plan_md = Path(str(approval.get("artifact_path") or ""))
    if not plan_md.exists():
        plan_md = approvals_dir / "modification-plan.md"
    plan_json = plan_md.with_suffix(".json")
    if not plan_json.exists():
        plan_json = approvals_dir / "modification-plan.json"
    return plan_md, plan_json


def _copy_source_artifacts(approval: dict[str, object], approvals_dir: Path, input_dir: Path) -> tuple[dict[str, str], list[str]]:
    issues: list[str] = []
    copied: dict[str, str] = {}
    plan_md, plan_json = _source_plan_paths(approval, approvals_dir)
    sources = {
        "modification-plan.md": plan_md,
        "modification-plan.json": plan_json,
        "dry-run.patch": approvals_dir / "dry-run.patch",
        "dry-run-validation-result.json": approvals_dir / "dry-run-validation-result.json",
        "patch-validation.json": approvals_dir / "patch-validation.json",
    }
    for name, source in sources.items():
        if not source.exists():
            issues.append(f"Required source artifact is missing: {source}")
            continue
        if source.is_symlink():
            issues.append(f"Source artifact must not be a symlink: {source}")
            continue
        destination = input_dir / name
        shutil.copy2(source, destination)
        copied[name] = str(destination)
    return copied, issues


def _plan_commands(plan: dict[str, Any]) -> list[Any]:
    commands = plan.get("proposed_commands")
    return commands if isinstance(commands, list) else []


def _report_markdown(result: dict[str, Any]) -> str:
    issues = result["issues"] or ["None."]
    return "\n".join(
        [
            "# Sandbox Run Report",
            "",
            f"Project id: {result['project_id']}",
            f"Approval id: {result['approval_id']}",
            f"Status: {result['status']}",
            f"Sandbox path: {result['sandbox_path']}",
            "",
            "## Safety",
            f"production_modified: {result['production_modified']}",
            f"global_registries_modified: {result['global_registries_modified']}",
            f"harness_modified: {result['harness_modified']}",
            "",
            "## Commands",
            f"executed: {len(result['commands_executed'])}",
            f"blocked: {len(result['commands_blocked'])}",
            "",
            "## Expected Outcome",
            str(result["expected_outcome_comparison"].get("status", "")),
            "",
            "## Issues",
            *[f"- {issue}" for issue in issues],
            "",
            "## Next Step",
            result["next_step"],
            "",
        ]
    )


def run_sandbox(project_id: str, approval_id: str, request: SandboxRunRequest) -> SandboxRunResponse:
    project = get_project_record(project_id)
    if not project:
        raise KeyError(project_id)
    approval = get_approval_record(approval_id)
    if not approval or str(approval["project_id"]) != project_id:
        raise KeyError(approval_id)
    if str(approval["status"]) != "approved":
        raise SandboxRunError("Sandbox run requires approval status approved.")

    project_root = Path(str(project["root_path"]))
    approvals_dir = project_root / "approvals"
    dry_run_result_path = approvals_dir / "dry-run-validation-result.json"
    if not dry_run_result_path.exists():
        raise SandboxRunError("Sandbox run requires prior dry-run validation result.")
    dry_run_result = _load_json(dry_run_result_path)
    if dry_run_result.get("status") != "passed":
        raise SandboxRunError("Sandbox run requires prior dry-run validation status passed.")

    record_event(project_id, None, "sandbox_run_started", {"approval_id": approval_id, "sandbox_mode": request.sandbox_mode})
    previous_result_path = project_root / "sandbox" / "sandbox-run-result.json"
    if previous_result_path.exists() and not previous_result_path.is_symlink():
        record_event(
            project_id,
            None,
            "sandbox_previous_result_recorded",
            {"approval_id": approval_id, "previous_result": _load_json(previous_result_path)},
        )
    paths = _prepare_sandbox(project_root)
    copied, copy_issues = _copy_source_artifacts(dict(approval), approvals_dir, paths["input"])
    record_event(project_id, None, "sandbox_input_copied", {"approval_id": approval_id, "copied": copied, "issues": copy_issues})

    report_path = paths["sandbox"] / "sandbox-run-report.md"
    result_path = paths["sandbox"] / "sandbox-run-result.json"
    command_log_path = paths["sandbox"] / "sandbox-command-log.json"
    manifest_path = paths["sandbox"] / "sandbox-file-manifest.json"
    applied_patch_path = paths["sandbox"] / "applied.patch"

    issues = list(copy_issues)
    patch_result: dict[str, object] = {"status": "passed", "issues": [], "sandbox_patch_applied": False}
    if request.sandbox_mode in {"patch_only", "full_sandbox"} and not issues:
        patch_result = apply_patch_in_sandbox(approvals_dir / "dry-run.patch", project_root, paths["workspace"], applied_patch_path)
        issues.extend(str(issue) for issue in patch_result.get("issues", []))
    elif not applied_patch_path.exists():
        applied_patch_path.write_text("", encoding="utf-8")
    record_event(project_id, None, "sandbox_patch_validated", {"approval_id": approval_id, "patch_result": patch_result})
    record_event(
        project_id,
        None,
        "sandbox_patch_applied_or_blocked",
        {"approval_id": approval_id, "status": patch_result["status"], "sandbox_patch_applied": patch_result.get("sandbox_patch_applied", False)},
    )

    plan = _load_json(paths["input"] / "modification-plan.json") if (paths["input"] / "modification-plan.json").exists() else {}
    command_log = (
        validate_and_maybe_run_commands(_plan_commands(plan), paths["sandbox"], request.allow_sandbox_commands)
        if request.sandbox_mode in {"plan_only", "full_sandbox"}
        else {"commands_reviewed": [], "commands_executed": [], "commands_blocked": [], "allow_sandbox_commands": request.allow_sandbox_commands}
    )
    _write_json(command_log_path, command_log)
    record_event(project_id, None, "sandbox_commands_validated", {"approval_id": approval_id, "command_log_path": str(command_log_path)})

    commands_blocked = list(command_log["commands_blocked"])
    if any(command.get("classification") == "blocked" for command in commands_blocked):
        issues.extend(f"Blocked command: {command['command']}" for command in commands_blocked if command.get("classification") == "blocked")

    expected_outcome = plan.get("expected_outcome") or plan.get("expected_result")
    expected_outcome_comparison = {
        "status": "not_specified" if not expected_outcome else "recorded_for_review",
        "expected_outcome": expected_outcome or "",
        "sandbox_patch_applied": bool(patch_result.get("sandbox_patch_applied", False)),
        "commands_executed_count": len(command_log["commands_executed"]),
    }

    status = "passed"
    if patch_result["status"] == "blocked" or any(command.get("classification") == "blocked" for command in commands_blocked):
        status = "blocked"
    elif issues or patch_result["status"] == "failed":
        status = "failed"

    manifest = {
        "sandbox_path": str(paths["sandbox"]),
        "input_files": copied,
        "workspace_files": [str(path) for path in paths["workspace"].rglob("*") if path.is_file()],
        "output_files": [str(path) for path in paths["output"].rglob("*") if path.is_file()],
        "logs": [str(path) for path in paths["logs"].rglob("*") if path.is_file()],
    }
    _write_json(manifest_path, manifest)

    next_step = (
        "Resolve blocked sandbox validation issues before any future promotion workflow."
        if status == "blocked"
        else "Resolve sandbox validation issues before any future promotion workflow."
        if status == "failed"
        else "Sandbox validation passed; v0.7 still does not modify production."
    )
    result: dict[str, Any] = {
        "project_id": project_id,
        "approval_id": approval_id,
        "status": status,
        "sandbox_path": str(paths["sandbox"]),
        "sandbox_report_path": str(report_path),
        "sandbox_result_path": str(result_path),
        "production_modified": False,
        "global_registries_modified": False,
        "harness_modified": False,
        "commands_executed": command_log["commands_executed"],
        "commands_blocked": commands_blocked,
        "issues": issues,
        "next_step": next_step,
        "patch_result": patch_result,
        "expected_outcome_comparison": expected_outcome_comparison,
        "manifest_path": str(manifest_path),
        "command_log_path": str(command_log_path),
    }
    _write_json(result_path, result)
    report_path.write_text(_report_markdown(result), encoding="utf-8")
    record_event(
        project_id,
        None,
        "sandbox_run_completed",
        {
            "approval_id": approval_id,
            "sandbox_status": status,
            "sandbox_result_path": str(result_path),
            "production_modified": False,
            "global_registries_modified": False,
            "harness_modified": False,
        },
        status=status,
    )

    return SandboxRunResponse(**result)
