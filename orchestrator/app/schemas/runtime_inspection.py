from typing import Literal

from pydantic import BaseModel, Field


RuntimeTargetType = Literal["cron", "systemd", "script", "docker", "python", "unknown"]


class RuntimeInspectRequest(BaseModel):
    target_type: RuntimeTargetType = "unknown"
    target_hint: str = ""
    allow_read_only_commands: bool = False


class RuntimeInspectResponse(BaseModel):
    project_id: str
    status: str
    runtime_inspection_report_path: str
    task_packet_path: str
    agent_result_path: str
    inspection_summary: str
    blockers: list[str] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    safe_to_modify: bool = False
