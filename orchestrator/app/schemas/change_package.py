from typing import Literal

from pydantic import BaseModel, Field


ChangePackageStatus = Literal["packaged", "blocked", "failed"]


class ChangePackageRequest(BaseModel):
    change_window: str = ""
    operator: str = ""
    notes: str = ""


class ChangePackageResponse(BaseModel):
    project_id: str
    approval_id: str
    status: ChangePackageStatus
    change_package_path: str = ""
    execution_checklist_path: str = ""
    rollback_checklist_path: str = ""
    preflight_checklist_path: str = ""
    postchange_checklist_path: str = ""
    final_approval_id: str = ""
    production_modified: bool = False
    global_registries_modified: bool = False
    harness_modified: bool = False
    issues: list[str] = Field(default_factory=list)
    next_step: str = ""


class ChangePackageRead(BaseModel):
    approval_id: str
    final_approval_id: str = ""
    status: str
    artifact_path: str
    created_at: str
    updated_at: str


class ChangePackagesResponse(BaseModel):
    project_id: str
    change_packages: list[ChangePackageRead] = Field(default_factory=list)
