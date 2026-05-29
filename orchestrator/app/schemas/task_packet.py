from pydantic import BaseModel, Field


class TaskPacket(BaseModel):
    project_id: str
    state: str = "INTAKE"
    request: str
    notes: list[str] = Field(default_factory=list)
