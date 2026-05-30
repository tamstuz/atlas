from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    request: str


class ProjectState(BaseModel):
    project_id: str
    name: str
    request: str
    status: str
    root_path: str
    workspace_path: str


class TaskSummary(BaseModel):
    task_id: str
    role: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None


class ProjectRead(ProjectState):
    task_summary: list[TaskSummary]
    final_report_path: str | None = None
