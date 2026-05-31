from typing import Literal

from pydantic import BaseModel, Field


ApprovalTransitionStatus = Literal["approved", "rejected"]
ValidationMode = Literal["patch_only", "plan_only", "full_dry_run"]
ValidationStatus = Literal["passed", "failed", "blocked"]


class ApprovalStatusRequest(BaseModel):
    status: ApprovalTransitionStatus
    reason: str = ""
    allow_blocked_approval: bool = False


class ApprovalStatusResponse(BaseModel):
    approval_id: str
    project_id: str
    approval_type: str
    status: str
    artifact_path: str
    reason: str = ""
    created_at: str
    updated_at: str


class DryRunValidationRequest(BaseModel):
    validation_mode: ValidationMode = "full_dry_run"


class DryRunValidationResponse(BaseModel):
    project_id: str
    approval_id: str
    status: ValidationStatus
    validation_report_path: str
    patch_validation_path: str
    production_modified: bool = False
    global_registries_modified: bool = False
    harness_modified: bool = False
    issues: list[str] = Field(default_factory=list)
    next_step: str = ""
