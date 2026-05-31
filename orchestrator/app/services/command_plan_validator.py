from __future__ import annotations

import shlex
from typing import Any


def _command_text(command: Any) -> str:
    if isinstance(command, str):
        return command.strip()
    if isinstance(command, dict):
        value = command.get("command") or command.get("cmd") or command.get("shell")
        return str(value).strip() if value is not None else ""
    return str(command).strip()


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def classify_command(command: Any) -> dict[str, object]:
    text = _command_text(command)
    tokens = _tokens(text)
    lowered = [token.lower() for token in tokens]
    reasons: list[str] = []
    classification = "unknown"

    if not tokens:
        return {"command": text, "classification": "unknown", "reasons": ["Command is empty."]}

    if lowered[0] == "sudo":
        classification = "blocked"
        reasons.append("sudo/root execution is blocked in v0.6.")
    if lowered[:2] == ["systemctl", "restart"] or lowered[:2] == ["systemctl", "stop"] or lowered[:2] == ["systemctl", "start"]:
        classification = "blocked"
        reasons.append("Service start/stop/restart is blocked in v0.6.")
    if lowered[:2] == ["systemctl", "enable"] or lowered[:2] == ["systemctl", "disable"]:
        classification = "blocked"
        reasons.append("Systemd enable/disable is blocked in v0.6.")
    if lowered[:2] == ["crontab", "-e"]:
        classification = "blocked"
        reasons.append("Cron editing is blocked in v0.6.")
    if lowered[:2] in (["apt", "install"], ["apt", "remove"], ["apt-get", "install"], ["apt-get", "remove"]):
        classification = "blocked"
        reasons.append("Package installation/removal is blocked in v0.6.")
    if lowered[0] in {"rm", "mv"}:
        classification = "blocked"
        reasons.append("File deletion or moving is blocked in v0.6 dry-run validation.")
    if lowered[0] == "cp" and any(token.startswith("/etc/") or token == "/etc" for token in lowered[1:]):
        classification = "blocked"
        reasons.append("Copying files into /etc is blocked in v0.6.")
    if lowered[:3] == ["docker", "compose", "up"] or lowered[:3] == ["docker", "compose", "down"]:
        classification = "blocked"
        reasons.append("Docker Compose up/down is blocked in v0.6.")

    if classification != "blocked" and (
        lowered[:3] == ["python", "-m", "compileall"]
        or lowered[:3] == ["python", "-m", "pytest"]
        or lowered[:2] == ["bash", "-n"]
        or lowered[:3] == ["git", "diff", "--check"]
    ):
        classification = "allowed_for_future_review"
        reasons.append("Read-only validation command; not executed by v0.6.")

    if not reasons:
        reasons.append("Command is recorded for future review and was not executed.")

    return {"command": text, "classification": classification, "reasons": reasons}


def validate_command_plan(commands: list[Any]) -> dict[str, object]:
    results = [classify_command(command) for command in commands]
    blocked = [item for item in results if item["classification"] == "blocked"]
    unknown = [item for item in results if item["classification"] == "unknown"]
    return {
        "commands": results,
        "blocked_count": len(blocked),
        "unknown_count": len(unknown),
        "commands_executed": False,
    }
