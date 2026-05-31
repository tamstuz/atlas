from __future__ import annotations

from pathlib import Path


FORBIDDEN_PREFIXES = (
    "/etc/",
    "/usr/lib/systemd/",
    "/lib/systemd/",
    "/etc/systemd/",
    "/var/spool/cron/",
    "/srv/ai-lab/harness/prod/",
    "/srv/ai-lab/runtime/registries/",
)


def _strip_patch_prefix(path: str) -> str:
    value = path.strip()
    if value in {"/dev/null", "dev/null"}:
        return value
    if value.startswith("a/") or value.startswith("b/"):
        return value[2:]
    return value


def _extract_targets(patch_text: str) -> list[str]:
    targets: list[str] = []
    for raw_line in patch_text.splitlines():
        line = raw_line.strip()
        if line.startswith("diff --git "):
            parts = line.split()
            targets.extend(_strip_patch_prefix(part) for part in parts[2:4])
        elif line.startswith("+++ ") or line.startswith("--- "):
            target = line.split(maxsplit=1)[1].split("\t", maxsplit=1)[0]
            targets.append(_strip_patch_prefix(target))
    return sorted({target for target in targets if target and target not in {"/dev/null", "dev/null"}})


def _is_forbidden(target: str) -> bool:
    normalized = target.replace("\\", "/")
    absolute = normalized if normalized.startswith("/") else f"/{normalized}"
    return any(absolute == prefix.rstrip("/") or absolute.startswith(prefix) for prefix in FORBIDDEN_PREFIXES)


def _is_candidate_target(target: str, project_root: Path) -> bool:
    normalized = target.replace("\\", "/")
    root = project_root.as_posix().rstrip("/")
    root_without_slash = root.lstrip("/")
    allowed_relative = ("workspace/", "approvals/")
    allowed_absolute = (
        f"{root}/workspace/",
        f"{root}/approvals/",
        f"{root_without_slash}/workspace/",
        f"{root_without_slash}/approvals/",
    )
    return normalized.startswith(allowed_relative) or normalized.startswith(allowed_absolute)


def validate_patch(patch_path: Path, project_root: Path, plan_blocked: bool = False) -> dict[str, object]:
    issues: list[str] = []
    targets: list[str] = []
    status = "passed"

    if not patch_path.exists():
        return {
            "status": "failed",
            "patch_path": str(patch_path),
            "targets": [],
            "issues": ["dry-run.patch is missing."],
            "patch_applied": False,
            "candidate_only": False,
        }

    patch_text = patch_path.read_text(encoding="utf-8")
    if not patch_text.strip() and not plan_blocked:
        issues.append("dry-run.patch is empty.")
        status = "failed"

    targets = _extract_targets(patch_text)
    forbidden = [target for target in targets if _is_forbidden(target)]
    non_candidate = [target for target in targets if not _is_candidate_target(target, project_root)]

    if forbidden:
        status = "blocked"
        issues.extend(f"Forbidden patch target: {target}" for target in forbidden)
    if non_candidate:
        status = "blocked"
        issues.extend(f"Patch target is not project-local candidate scope: {target}" for target in non_candidate)

    return {
        "status": status,
        "patch_path": str(patch_path),
        "targets": targets,
        "issues": issues,
        "patch_applied": False,
        "candidate_only": not forbidden and not non_candidate,
    }
