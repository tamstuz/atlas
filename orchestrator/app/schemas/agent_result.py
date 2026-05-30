from pydantic import BaseModel, Field


class AgentResult(BaseModel):
    role: str
    status: str = "complete"
    notes: list[str] = Field(default_factory=list)
