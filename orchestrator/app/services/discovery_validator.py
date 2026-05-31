DISCOVERY_REQUIREMENTS = {
    "scheduler_source": "Scheduler/source",
    "exact_command": "Exact command",
    "runtime_working_directory": "Runtime working directory",
    "absolute_script_path": "Absolute script path",
    "config_files": "Config files",
    "log_files": "Log files",
    "verification_command": "Verification command",
    "owner_service_context": "Owner/service context",
    "current_observed_behavior": "Current observed behavior",
    "proposed_next_step": "Proposed next step",
}


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | set | dict):
        return bool(value)
    return True


def validate_discovery(findings: dict[str, object]) -> dict[str, object]:
    satisfied = []
    missing = []
    for key, label in DISCOVERY_REQUIREMENTS.items():
        if _has_value(findings.get(key)):
            satisfied.append(label)
        else:
            missing.append(label)

    if missing:
        confidence = "medium" if len(satisfied) >= len(DISCOVERY_REQUIREMENTS) // 2 else "low"
        return {
            "safe_to_modify": False,
            "missing_requirements": missing,
            "satisfied_requirements": satisfied,
            "confidence": confidence,
            "reason": "Discovery is incomplete; v0.4 remains read-only and requires all fields before future modification approval.",
        }

    return {
        "safe_to_modify": True,
        "missing_requirements": [],
        "satisfied_requirements": satisfied,
        "confidence": "high",
        "reason": "All discover-before-modify requirements are present. v0.4 still does not perform modifications.",
    }
