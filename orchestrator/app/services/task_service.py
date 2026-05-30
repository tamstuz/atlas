from collections.abc import Mapping
from datetime import UTC, datetime

from .. import db

TASK_ROLES = ["intake", "analyst", "architect", "developer", "qa", "final_report", "runtime_inspector"]
DEFAULT_WORKFLOW_ROLES = ["intake", "analyst", "architect", "developer", "qa", "final_report"]


def create_initial_tasks(project_id: str) -> list[Mapping[str, object]]:
    tasks = []
    for role in TASK_ROLES:
        row = db.execute_returning(
            """
            INSERT INTO tasks (project_id, title, status, assigned_role, phase)
            VALUES (%s, %s, 'pending', %s, %s)
            RETURNING id, project_id, title, status, assigned_role, phase, started_at, completed_at
            """,
            (project_id, f"{role} task", role, role),
        )
        tasks.append(row)
    return tasks


def get_project_tasks(project_id: str) -> list[Mapping[str, object]]:
    return db.fetch_all(
        """
        SELECT id, project_id, title, status, assigned_role, phase, started_at, completed_at
        FROM tasks
        WHERE project_id = %s
        ORDER BY created_at ASC
        """,
        (project_id,),
    )


def get_task_for_role(project_id: str, role: str) -> Mapping[str, object] | None:
    return db.fetch_one(
        """
        SELECT id, project_id, title, status, assigned_role, phase, started_at, completed_at
        FROM tasks
        WHERE project_id = %s AND assigned_role = %s
        ORDER BY created_at ASC
        LIMIT 1
        """,
        (project_id, role),
    )


def set_task_status(task_id: str, status: str) -> None:
    now = datetime.now(UTC)
    started = ", started_at = COALESCE(started_at, %s)" if status == "running" else ""
    completed = ", completed_at = %s" if status in {"complete", "failed", "blocked"} else ""
    params: tuple[object, ...]
    if status == "running":
        params = (status, now, task_id)
    elif status in {"complete", "failed", "blocked"}:
        params = (status, now, task_id)
    else:
        params = (status, task_id)
    db.execute(f"UPDATE tasks SET status = %s{started}{completed}, updated_at = now() WHERE id = %s", params)
