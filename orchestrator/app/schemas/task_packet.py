from pydantic import BaseModel, Field


class TaskPacket(BaseModel):
    project_id: str
    task_id: str
    role: str
    phase: str
    objective: str
    input_summary: str
    harness_files_loaded: list[str] = Field(default_factory=list)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    expected_output: str
    definition_of_done: str
    created_at: str
