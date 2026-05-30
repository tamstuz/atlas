import json
import uuid
from collections.abc import Mapping
from pathlib import Path

from .. import db
from ..config import settings
from ..schemas.project_state import ProjectCreate, ProjectRead, ProjectState, TaskSummary
from .task_service import create_initial_tasks, get_project_tasks


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _append_decision(root: Path, text: str) -> None:
    with (root / "decision-log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"- {text}\n")


def _task_board_payload(tasks: list[Mapping[str, object]]) -> dict:
    return {
        "tasks": [
            {
                "task_id": str(task["id"]),
                "role": str(task["assigned_role"]),
                "status": str(task["status"]),
                "started_at": task.get("started_at"),
                "completed_at": task.get("completed_at"),
            }
            for task in tasks
        ]
    }


def write_project_files(project: Mapping[str, object], tasks: list[Mapping[str, object]], final_report_path: str = "") -> None:
    root = Path(str(project["root_path"]))
    state = {
        "project_id": str(project["id"]),
        "name": str(project["name"]),
        "request": str(project["request"]),
        "status": str(project["status"]),
        "current_phase": str(project.get("current_phase") or ""),
        "created_at": project.get("created_at"),
        "updated_at": project.get("updated_at"),
        "final_report_path": final_report_path,
    }
    _write_json(root / "project-state.json", state)
    _write_json(root / "task-board.json", _task_board_payload(tasks))


def create_project(payload: ProjectCreate) -> ProjectState:
    project_id = str(uuid.uuid4())
    root = settings.projects_dir / project_id
    for child in ["workspace", "handoffs", "qa", "final"]:
        (root / child).mkdir(parents=True, exist_ok=True)

    project = db.execute_returning(
        """
        INSERT INTO projects (id, name, request, root_path, status)
        VALUES (%s, %s, %s, %s, 'new')
        RETURNING id, name, request, status, root_path, created_at, updated_at
        """,
        (project_id, payload.name, payload.request, str(root)),
    )
    tasks = create_initial_tasks(project_id)
    (root / "decision-log.md").write_text("# Decision Log\n\n", encoding="utf-8")
    _append_decision(root, "Created project")
    write_project_files(project, tasks)
    return ProjectState(
        project_id=project_id,
        name=payload.name,
        request=payload.request,
        status=str(project["status"]),
        root_path=str(root),
        workspace_path=str(root / "workspace"),
    )


def get_project_record(project_id: str) -> Mapping[str, object] | None:
    return db.fetch_one(
        """
        SELECT id, name, request, status, root_path, created_at, updated_at
        FROM projects
        WHERE id = %s
        """,
        (project_id,),
    )


def update_project_status(project_id: str, status: str) -> Mapping[str, object]:
    return db.execute_returning(
        """
        UPDATE projects
        SET status = %s, updated_at = now()
        WHERE id = %s
        RETURNING id, name, request, status, root_path, created_at, updated_at
        """,
        (status, project_id),
    )


def get_project(project_id: str) -> ProjectRead | None:
    project = get_project_record(project_id)
    if not project:
        return None

    root = Path(str(project["root_path"]))
    tasks = get_project_tasks(project_id)
    final_report = root / "final" / "final-report.md"
    return ProjectRead(
        project_id=str(project["id"]),
        name=str(project["name"]),
        request=str(project["request"]),
        status=str(project["status"]),
        root_path=str(root),
        workspace_path=str(root / "workspace"),
        task_summary=[
            TaskSummary(
                task_id=str(task["id"]),
                role=str(task["assigned_role"]),
                status=str(task["status"]),
                started_at=str(task["started_at"]) if task.get("started_at") else None,
                completed_at=str(task["completed_at"]) if task.get("completed_at") else None,
            )
            for task in tasks
        ],
        final_report_path=str(final_report) if final_report.exists() else None,
    )


def append_decision_for_project(project_id: str, text: str) -> None:
    project = get_project_record(project_id)
    if project:
        _append_decision(Path(str(project["root_path"])), text)
