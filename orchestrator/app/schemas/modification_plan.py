from typing import Literal

from pydantic import BaseModel, Field

from .runtime_inspection import RuntimeTargetType


class ModificationPlanRequest(BaseModel):
    change_request: str
    target_type: RuntimeTargetType = "unknown"
    target_hint: str = ""
    allow_plan_with_blockers: bool = False


class ModificationPlanResponse(BaseModel):
    project_id: str
    status: Literal["blocked", "pending_approval", "failed"]
    approval_id: str = ""
    safe_to_modify: bool = False
    plan_path: str = ""
    dry_run_patch_path: str = ""
    approval_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    next_step: str = ""


class ApprovalRead(BaseModel):
    approval_id: str
    approval_type: str
    status: str
    artifact_path: str
    created_at: str
    updated_at: str


class ApprovalsResponse(BaseModel):
    project_id: str
    approvals: list[ApprovalRead] = Field(default_factory=list)
