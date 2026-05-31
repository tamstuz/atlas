import subprocess
from dataclasses import dataclass


MAX_OUTPUT_CHARS = 4000
SHELL_METACHARS = set(";|&><$`\\\n\r")
BLOCKED_WORDS = {
    "sudo",
    "su",
    "rm",
    "rmdir",
    "mv",
    "cp",
    "touch",
    "tee",
    "chmod",
    "chown",
    "install",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "systemctl restart",
    "systemctl stop",
    "systemctl start",
    "systemctl enable",
    "systemctl disable",
    "crontab -e",
    "curl",
    "wget",
    "nc",
    "nmap",
    "ssh",
}


@dataclass(frozen=True)
class InspectionCommand:
    args: list[str]
    purpose: str


def build_command_plan(target_type: str = "unknown", target_hint: str = "") -> list[InspectionCommand]:
    hint = target_hint.strip()
    plan = [
        InspectionCommand(["pwd"], "Capture current working directory context."),
        InspectionCommand(["whoami"], "Capture runtime user context."),
        InspectionCommand(["hostname"], "Capture host context."),
        InspectionCommand(["date"], "Timestamp the inspection environment."),
    ]
    if target_type == "systemd":
        service = hint or "<service-name>"
        plan.extend(
            [
                InspectionCommand(["systemctl", "status", service], "Inspect service status without modification."),
                InspectionCommand(["systemctl", "cat", service], "Read unit files without modification."),
                InspectionCommand(["journalctl", "-n", "100"], "Read recent logs without modification."),
            ]
        )
    elif target_type == "cron":
        plan.append(InspectionCommand(["crontab", "-l"], "Read current user's crontab without modification."))
    elif target_type == "docker":
        plan.extend(
            [
                InspectionCommand(["docker", "ps"], "List running containers."),
                InspectionCommand(["docker", "compose", "ps"], "List compose services."),
            ]
        )
    elif target_type in {"script", "python"} and hint:
        plan.append(InspectionCommand(["ls", "-l", hint], "Inspect the hinted path metadata without modification."))
    return plan


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + "\n[output truncated]"


def _contains_metachar(args: list[str]) -> bool:
    return any(any(char in arg for char in SHELL_METACHARS) for arg in args)


def _blocked(args: list[str]) -> str:
    joined = " ".join(args).lower()
    for word in BLOCKED_WORDS:
        if word in joined:
            return word
    return ""


def is_allowlisted(args: list[str]) -> bool:
    if not args:
        return False
    first = args[0]
    if first in {"pwd", "whoami", "hostname", "date", "ls", "find", "cat", "grep"}:
        return True
    if args[:2] in (["systemctl", "status"], ["systemctl", "cat"], ["systemctl", "list-timers"]):
        return True
    if args[:2] == ["crontab", "-l"]:
        return True
    if args[:2] == ["docker", "ps"]:
        return True
    if args[:3] == ["docker", "compose", "ps"]:
        return True
    if args[:2] == ["docker", "inspect"]:
        return True
    if args[:2] == ["journalctl", "-n"]:
        return True
    return False


def inspect_command(args: list[str], commands_enabled: bool = False, timeout_seconds: float = 5.0) -> dict[str, object]:
    command = " ".join(args)
    if _contains_metachar(args):
        return {"command": command, "status": "rejected", "reason": "Shell metacharacters are not allowed."}
    blocked = _blocked(args)
    if blocked:
        return {"command": command, "status": "rejected", "reason": f"Blocked command or token: {blocked}"}
    if not is_allowlisted(args):
        return {"command": command, "status": "rejected", "reason": "Command is not in the v0.4 read-only allowlist."}
    if not commands_enabled:
        return {"command": command, "status": "skipped", "reason": "Read-only command execution is disabled."}

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"command": command, "status": "failed", "reason": str(exc), "exit_code": None}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "status": "failed", "reason": f"Command timed out after {timeout_seconds} seconds.", "stdout": _truncate(exc.stdout or ""), "stderr": _truncate(exc.stderr or ""), "exit_code": None}

    return {
        "command": command,
        "status": "complete" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout": _truncate(completed.stdout),
        "stderr": _truncate(completed.stderr),
    }
