import json
from pathlib import Path

from ..schemas.task_packet import TaskPacket


def load_schema_text(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, indent=2)


def assemble_prompt(
    role: str,
    harness_files: list[dict[str, str]],
    task_packet: TaskPacket,
    project_request: str,
    output_schema: str,
) -> str:
    harness_sections = "\n\n".join(
        f"## Harness File: {item['path']}\n{item['content']}" for item in harness_files
    )
    packet_json = json.dumps(task_packet.model_dump(), indent=2)
    return "\n".join(
        [
            f"You are the {role} specialist for AI Lab Orchestrator.",
            "",
            "Follow only the loaded harness instructions and task packet scope.",
            "Do not modify harness/prod, create skills, perform self-improvement, or add a web UI.",
            "",
            "# Loaded Harness",
            harness_sections,
            "",
            "# Project Request",
            project_request,
            "",
            "# Task Packet",
            packet_json,
            "",
            "# Required Output Schema",
            output_schema,
            "",
            "Return concise structured content suitable for the agent result summary.",
        ]
    )
