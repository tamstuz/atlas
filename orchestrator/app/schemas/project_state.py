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
