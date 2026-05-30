from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    project_id: str
    task_id: str
    role: str
    status: str = "complete"
    summary: str
    artifacts_created: list[str] = Field(default_factory=list)
    files_read: list[str] = Field(default_factory=list)
    files_written: list[str] = Field(default_factory=list)
    harness_files_loaded: list[str] = Field(default_factory=list)
    next_recommended_role: str = ""
    blockers: list[str] = Field(default_factory=list)
    created_at: str
