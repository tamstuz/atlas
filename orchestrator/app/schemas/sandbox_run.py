from typing import Literal

from pydantic import BaseModel, Field


SandboxMode = Literal["patch_only", "plan_only", "full_sandbox"]
SandboxStatus = Literal["passed", "failed", "blocked"]


class SandboxRunRequest(BaseModel):
    sandbox_mode: SandboxMode = "full_sandbox"
    allow_sandbox_commands: bool = False


class SandboxRunResponse(BaseModel):
    project_id: str
    approval_id: str
    status: SandboxStatus
    sandbox_path: str
    sandbox_report_path: str
    sandbox_result_path: str
    production_modified: bool = False
    global_registries_modified: bool = False
    harness_modified: bool = False
    commands_executed: list[dict[str, object]] = Field(default_factory=list)
    commands_blocked: list[dict[str, object]] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    next_step: str = ""
