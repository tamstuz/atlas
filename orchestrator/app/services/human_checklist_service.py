from __future__ import annotations

from typing import Any


PREFLIGHT_ITEMS = (
    "Confirm maintenance window is active.",
    "Confirm backup or snapshot is complete.",
    "Confirm current service status is documented.",
    "Confirm exact target file paths.",
    "Confirm exact command paths.",
    "Confirm no autonomous execution is active.",
)

EXECUTION_ITEMS = (
    "Confirm who is executing the change.",
    "Confirm who is approving the change.",
    "Review every human-only command before typing it.",
    "Stop if any command differs from the reviewed package.",
    "Record command output for post-change review.",
)

ROLLBACK_ITEMS = (
    "Confirm rollback owner.",
    "Confirm rollback command or path.",
    "Confirm backup or snapshot location.",
    "Stop the change if rollback prerequisites are missing.",
    "Run post-rollback verification after any rollback.",
)

POSTCHANGE_ITEMS = (
    "Confirm post-change validation command.",
    "Confirm expected service status.",
    "Confirm project artifacts remain under the project folder.",
    "Confirm no global registry files were modified by the agent.",
    "Confirm no harness/prod files were modified by the agent.",
)


def markdown_checklist(title: str, items: tuple[str, ...], metadata: dict[str, Any]) -> str:
    lines = [
        f"# {title}",
        "",
        f"Project id: {metadata['project_id']}",
        f"Approval id: {metadata['approval_id']}",
        f"Change window: {metadata.get('change_window') or '(not specified)'}",
        f"Operator: {metadata.get('operator') or '(not specified)'}",
        "",
        "Agents must not execute production changes. This checklist is for human review and execution only.",
        "",
        "## Checklist",
        *[f"- [ ] {item}" for item in items],
        "",
    ]
    return "\n".join(lines)
