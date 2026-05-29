from fastapi import FastAPI, HTTPException

from .config import settings
from .schemas.project_state import ProjectCreate, ProjectState
from .services.project_service import create_project, get_project

app = FastAPI(title="AI Lab Orchestrator", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-lab-orchestrator"}


@app.get("/config")
def config() -> dict:
    return settings.safe_config()


@app.post("/projects", response_model=ProjectState)
def post_project(payload: ProjectCreate) -> ProjectState:
    return create_project(payload)


@app.get("/projects/{project_id}", response_model=ProjectState)
def get_project_by_id(project_id: str) -> ProjectState:
    project = get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project
