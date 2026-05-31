from pathlib import Path

from ..config import settings

ROLE_FILES = {
    "intake": "roles/orchestrator.md",
    "analyst": "roles/analyst.md",
    "architect": "roles/architect.md",
    "developer": "roles/developer.md",
    "qa": "roles/qa.md",
    "final_report": "roles/final-report-writer.md",
    "runtime_inspector": "roles/runtime-inspector.md",
}

COMMON_RULES = [
    "workflow-rules/handoff-policy.md",
    "workflow-rules/completion-gates.md",
]

RUNTIME_INSPECTOR_RULES = [
    "runtime-control/discover-before-modify.md",
    "runtime-control/absolute-path-policy.md",
    "runtime-control/cron-debug-policy.md",
    "runtime-control/service-debug-policy.md",
]


class HarnessFileMissing(FileNotFoundError):
    pass


def active_harness_path() -> Path:
    return settings.harness_dir


def load_role_bundle(role: str) -> dict[str, object]:
    if role not in ROLE_FILES:
        raise HarnessFileMissing(f"No harness role mapping exists for role '{role}'.")

    relative_paths = [ROLE_FILES[role], *COMMON_RULES]
    if role == "runtime_inspector":
        relative_paths.extend(RUNTIME_INSPECTOR_RULES)

    files = []
    for relative_path in relative_paths:
        path = settings.harness_dir / relative_path
        if not path.exists():
            raise HarnessFileMissing(f"Required harness file is missing: {path}")
        files.append({"path": str(path), "content": path.read_text(encoding="utf-8")})

    return {"role": role, "files": files}
