from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any


BLOCKED_PREFIXES = (
    "sudo",
    "systemctl",
    "service",
    "crontab",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "rm",
    "mv",
    "chmod",
    "chown",
    "curl",
    "wget",
    "ssh",
    "scp",
)


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


def _is_allowed(tokens: list[str]) -> bool:
    lowered = [token.lower() for token in tokens]
    if lowered == ["pwd"] or (lowered and lowered[0] in {"ls", "find"}):
        return True
    if lowered and lowered[0] in {"cat", "grep"}:
        return True
    if lowered[:3] in (["python3", "-m", "py_compile"], ["python3", "-m", "compileall"]):
        return True
    if lowered[:2] == ["bash", "-n"]:
        return True
    if lowered[:3] == ["git", "apply", "--check"]:
        return True
    return False


def classify_sandbox_command(command: Any) -> dict[str, object]:
    text = _command_text(command)
    tokens = _tokens(text)
    lowered = [token.lower() for token in tokens]

    if not tokens:
        return {"command": text, "classification": "blocked", "reasons": ["Command is empty."]}
    if lowered[0] in BLOCKED_PREFIXES:
        return {"command": text, "classification": "blocked", "reasons": [f"{tokens[0]} is blocked in v0.7 sandbox validation."]}
    if lowered[:3] in (["docker", "compose", "up"], ["docker", "compose", "down"]) or lowered[:2] == ["docker", "run"]:
        return {"command": text, "classification": "blocked", "reasons": ["Docker execution is blocked in v0.7."]}
    if lowered[0] == "cp" and any(token.startswith("/etc/") or token == "/etc" for token in lowered[1:]):
        return {"command": text, "classification": "blocked", "reasons": ["Copying into /etc is blocked in v0.7."]}
    if _is_allowed(tokens):
        return {"command": text, "classification": "allowed_sandbox", "reasons": ["Allowed only inside the project sandbox."]}
    return {"command": text, "classification": "blocked", "reasons": ["Command is not in the v0.7 sandbox allowlist."]}


def _bounded(value: str | None, limit: int = 4000) -> str:
    text = value or ""
    return text[:limit]


def validate_and_maybe_run_commands(commands: list[Any], sandbox_path: Path, allow_sandbox_commands: bool) -> dict[str, object]:
    executed: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    reviewed: list[dict[str, object]] = []

    for command in commands:
        classified = classify_sandbox_command(command)
        reviewed.append(classified)
        if classified["classification"] != "allowed_sandbox":
            blocked.append(classified)
            continue
        if not allow_sandbox_commands:
            blocked.append({**classified, "classification": "not_executed", "reasons": ["Sandbox command execution is disabled."]})
            continue

        tokens = _tokens(str(classified["command"]))
        try:
            completed = subprocess.run(
                tokens,
                cwd=sandbox_path,
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            executed.append(
                {
                    **classified,
                    "exit_code": completed.returncode,
                    "stdout": _bounded(completed.stdout),
                    "stderr": _bounded(completed.stderr),
                }
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            executed.append({**classified, "exit_code": None, "stdout": "", "stderr": _bounded(str(exc))})

    return {
        "commands_reviewed": reviewed,
        "commands_executed": executed,
        "commands_blocked": blocked,
        "allow_sandbox_commands": allow_sandbox_commands,
    }
