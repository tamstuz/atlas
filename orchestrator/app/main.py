import logging

from fastapi import FastAPI, HTTPException

from . import llm
from .config import settings
from .db import DatabaseUnavailable
from .schemas.approval_status import (
    ApprovalStatusRequest,
    ApprovalStatusResponse,
    DryRunValidationRequest,
    DryRunValidationResponse,
)
from .schemas.modification_plan import ApprovalsResponse, ModificationPlanRequest, ModificationPlanResponse
from .schemas.project_state import ProjectCreate, ProjectRead, ProjectState
from .schemas.runtime_inspection import RuntimeInspectRequest, RuntimeInspectResponse
from .schemas.sandbox_run import SandboxRunRequest, SandboxRunResponse
from .services.approval_transition_service import ApprovalTransitionError, transition_approval_status
from .services.dry_run_validation_service import DryRunValidationError, run_dry_run_validation
from .services.project_service import ProjectCreationError, create_project, get_project
from .services.modification_planning_service import create_modification_plan, list_project_approvals
from .services.runtime_inspection_service import run_runtime_inspection
from .services.sandbox_service import SandboxRunError, run_sandbox
from .services.workflow_service import run_project_workflow

app = FastAPI(title="AI Lab Orchestrator", version="0.7.0")
logger = logging.getLogger(__name__)


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
        logger.exception("Project creation failed because PostgreSQL is unavailable.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProjectCreationError as exc:
        logger.exception("Project creation failed.")
        raise HTTPException(
            status_code=500,
            detail={"error": str(exc), "project_id": exc.project_id, "root_path": exc.root_path},
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected project creation failure.")
        raise HTTPException(status_code=500, detail={"error": f"Project creation failed: {exc}"}) from exc


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


@app.post("/projects/{project_id}/runtime-inspect", response_model=RuntimeInspectResponse)
def runtime_inspect(project_id: str, payload: RuntimeInspectRequest | None = None) -> RuntimeInspectResponse:
    try:
        return run_runtime_inspection(project_id, payload or RuntimeInspectRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Runtime inspection failed.")
        raise HTTPException(status_code=500, detail={"error": f"Runtime inspection failed: {exc}"}) from exc


@app.post("/projects/{project_id}/modification-plan", response_model=ModificationPlanResponse)
def modification_plan(project_id: str, payload: ModificationPlanRequest) -> ModificationPlanResponse:
    try:
        return create_modification_plan(project_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Modification planning failed.")
        raise HTTPException(status_code=500, detail={"error": f"Modification planning failed: {exc}"}) from exc


@app.get("/projects/{project_id}/approvals", response_model=ApprovalsResponse)
def get_approvals(project_id: str) -> ApprovalsResponse:
    try:
        return list_project_approvals(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project not found") from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/projects/{project_id}/approvals/{approval_id}/status", response_model=ApprovalStatusResponse)
def post_approval_status(project_id: str, approval_id: str, payload: ApprovalStatusRequest) -> ApprovalStatusResponse:
    try:
        return transition_approval_status(project_id, approval_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or approval not found") from exc
    except ApprovalTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/projects/{project_id}/approvals/{approval_id}/dry-run", response_model=DryRunValidationResponse)
def post_approval_dry_run(
    project_id: str,
    approval_id: str,
    payload: DryRunValidationRequest | None = None,
) -> DryRunValidationResponse:
    try:
        return run_dry_run_validation(project_id, approval_id, payload or DryRunValidationRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or approval not found") from exc
    except DryRunValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/projects/{project_id}/approvals/{approval_id}/sandbox-run", response_model=SandboxRunResponse)
def post_approval_sandbox_run(
    project_id: str,
    approval_id: str,
    payload: SandboxRunRequest | None = None,
) -> SandboxRunResponse:
    try:
        return run_sandbox(project_id, approval_id, payload or SandboxRunRequest())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Project or approval not found") from exc
    except SandboxRunError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/llm/status")
async def llm_status() -> dict[str, object]:
    return await llm.status()
