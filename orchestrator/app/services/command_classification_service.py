from __future__ import annotations

import shlex
from typing import Any


BLOCKED_PATTERNS = (
    "sudo",
    "systemctl restart",
    "systemctl start",
    "systemctl stop",
    "systemctl enable",
    "systemctl disable",
    "service restart",
    "crontab -e",
    "apt install",
    "apt remove",
    "apt-get install",
    "apt-get remove",
    "rm",
    "mv",
    "cp /etc",
    "docker compose up",
    "docker compose down",
    "docker run",
    "chmod",
    "chown",
)


def command_text(command: Any) -> str:
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


def _contains_blocked_pattern(command: str, tokens: list[str]) -> list[str]:
    lowered_command = command.lower()
    lowered_tokens = [token.lower() for token in tokens]
    reasons: list[str] = []
    for pattern in BLOCKED_PATTERNS:
        pattern_tokens = pattern.split()
        if len(pattern_tokens) == 1:
            if pattern_tokens[0] in lowered_tokens:
                reasons.append(f"Contains blocked pattern: {pattern}.")
        elif pattern in lowered_command:
            reasons.append(f"Contains blocked pattern: {pattern}.")
    if lowered_tokens and lowered_tokens[0] == "cp" and any(token == "/etc" or token.startswith("/etc/") for token in lowered_tokens[1:]):
        reasons.append("Contains blocked pattern: cp /etc.")
    if "service" in lowered_tokens and "restart" in lowered_tokens:
        reasons.append("Contains blocked pattern: service restart.")
    return reasons


def classify_human_command(command: Any) -> dict[str, object]:
    text = command_text(command)
    tokens = _tokens(text)
    if not tokens:
        return {
            "command": text,
            "classification": ["human_only"],
            "human_only": True,
            "blocked_for_agent": False,
            "warning": "Empty command recorded for human review only.",
            "reasons": ["Command is empty."],
        }

    reasons = _contains_blocked_pattern(text, tokens)
    categories = ["human_only"]
    blocked_for_agent = bool(reasons)
    if blocked_for_agent:
        categories.append("blocked_for_agent")

    lowered = [token.lower() for token in tokens]
    if lowered[0] in {"cat", "grep", "rg", "find", "ls", "pwd", "python", "bash", "git", "curl"}:
        categories.append("informational")
    else:
        categories.append("modifying" if blocked_for_agent else "informational")
    if "sudo" in lowered or any(reason.startswith("Contains blocked pattern: systemctl") for reason in reasons):
        categories.append("privileged")

    warning = (
        "Dangerous or privileged command. Agents must not execute this command; human review and execution only."
        if blocked_for_agent
        else "Human review only. v0.8 does not execute production commands."
    )
    return {
        "command": text,
        "classification": sorted(set(categories)),
        "human_only": True,
        "blocked_for_agent": blocked_for_agent,
        "warning": warning,
        "reasons": reasons or ["Command is written for human review only and was not executed."],
    }


def classify_human_commands(commands: list[Any]) -> dict[str, object]:
    classified = [classify_human_command(command) for command in commands]
    return {
        "commands": classified,
        "blocked_for_agent_count": sum(1 for command in classified if command["blocked_for_agent"]),
        "human_only_count": len(classified),
        "commands_executed": False,
    }
