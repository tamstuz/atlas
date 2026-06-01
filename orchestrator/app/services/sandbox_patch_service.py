from __future__ import annotations

from pathlib import Path, PurePosixPath

from .patch_validation_service import validate_patch


def _strip_prefix(path: str) -> str:
    value = path.strip()
    if value.startswith("a/") or value.startswith("b/"):
        value = value[2:]
    if value.startswith("/"):
        parts = value.split("/projects/", 1)
        if len(parts) == 2 and "/" in parts[1]:
            value = parts[1].split("/", 1)[1]
    if value.startswith("workspace/"):
        value = value[len("workspace/") :]
    return value


def _safe_workspace_path(workspace: Path, target: str) -> Path:
    relative = PurePosixPath(_strip_prefix(target))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Patch target escapes sandbox workspace: {target}")
    resolved = (workspace / Path(*relative.parts)).resolve()
    workspace_resolved = workspace.resolve()
    if workspace_resolved != resolved and workspace_resolved not in resolved.parents:
        raise ValueError(f"Patch target escapes sandbox workspace: {target}")
    return resolved


def _apply_simple_unified_patch(patch_text: str, workspace: Path) -> tuple[bool, list[str]]:
    issues: list[str] = []
    lines = patch_text.splitlines()
    current_target: Path | None = None
    additions: list[str] = []
    saw_hunk = False

    for line in lines:
        if line.startswith("+++ "):
            target = line.split(maxsplit=1)[1].split("\t", maxsplit=1)[0]
            if target not in {"/dev/null", "dev/null"}:
                current_target = _safe_workspace_path(workspace, target)
                additions = []
        elif line.startswith("@@ "):
            saw_hunk = True
        elif saw_hunk and current_target is not None:
            if line.startswith("+") and not line.startswith("+++ "):
                additions.append(line[1:])
            elif line.startswith(" ") and additions:
                additions.append(line[1:])

    if current_target is None:
        return True, issues

    current_target.parent.mkdir(parents=True, exist_ok=True)
    current_target.write_text("\n".join(additions) + ("\n" if additions else ""), encoding="utf-8")
    return True, issues


def apply_patch_in_sandbox(patch_path: Path, project_root: Path, sandbox_workspace: Path, applied_patch_path: Path) -> dict[str, object]:
    validation = validate_patch(patch_path, project_root)
    if validation["status"] != "passed":
        return {**validation, "sandbox_patch_applied": False}

    patch_text = patch_path.read_text(encoding="utf-8")
    targets = [str(target) for target in validation["targets"]]
    issues: list[str] = []
    for target in targets:
        try:
            _safe_workspace_path(sandbox_workspace, target)
        except ValueError as exc:
            issues.append(str(exc))
    if issues:
        return {**validation, "status": "blocked", "issues": [*validation["issues"], *issues], "sandbox_patch_applied": False}

    applied_patch_path.write_text(patch_text, encoding="utf-8")
    try:
        _, apply_issues = _apply_simple_unified_patch(patch_text, sandbox_workspace)
    except ValueError as exc:
        return {**validation, "status": "blocked", "issues": [*validation["issues"], str(exc)], "sandbox_patch_applied": False}

    return {
        **validation,
        "status": "failed" if apply_issues else "passed",
        "issues": [*validation["issues"], *apply_issues],
        "sandbox_patch_applied": not apply_issues,
        "applied_patch_path": str(applied_patch_path),
    }
