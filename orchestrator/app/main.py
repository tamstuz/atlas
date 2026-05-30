from fastapi import FastAPI, HTTPException

from . import llm
from .config import settings
from .db import DatabaseUnavailable
from .schemas.project_state import ProjectCreate, ProjectRead, ProjectState
from .services.project_service import create_project, get_project
from .services.workflow_service import run_project_workflow

app = FastAPI(title="AI Lab Orchestrator", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai-lab-orchestrator"}


@app.get("/config")
def config() -> dict:
    return settings.safe_config()


@app.post("/projects", response_model=ProjectState)
def post_project(payload: ProjectCreate) -> ProjectState:
    try:
        return create_project(payload)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/projects/{project_id}", response_model=ProjectRead)
def get_project_by_id(project_id: str) -> ProjectRead:
    try:
        project = get_project(project_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/projects/{project_id}/run")
def run_project(project_id: str) -> dict:
    try:
        return run_project_workflow(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/llm/status")
async def llm_status() -> dict[str, object]:
    return await llm.status()
