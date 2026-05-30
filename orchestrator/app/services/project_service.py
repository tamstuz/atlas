import json
import uuid
from pathlib import Path

from ..config import settings
from ..db import create_project_record, get_project_record
from ..schemas.project_state import ProjectCreate, ProjectState


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create_project(payload: ProjectCreate) -> ProjectState:
    project_id = str(uuid.uuid4())
    root = settings.projects_dir / project_id
    for child in ["workspace", "handoffs", "qa", "final"]:
        (root / child).mkdir(parents=True, exist_ok=True)

    state = {
        "project_id": project_id,
        "name": payload.name,
        "request": payload.request,
        "status": "new",
        "root_path": str(root),
        "workspace_path": str(root / "workspace"),
    }
    _write_json(root / "project-state.json", state)
    _write_json(root / "task-board.json", {"tasks": []})
    (root / "decision-log.md").write_text("# Decision Log\n\n", encoding="utf-8")
    create_project_record(project_id, payload.name, payload.request, str(root))
    return ProjectState(**state)


def get_project(project_id: str) -> ProjectState | None:
    root = settings.projects_dir / project_id
    state_file = root / "project-state.json"
    if state_file.exists():
        return ProjectState(**json.loads(state_file.read_text(encoding="utf-8")))

    record = get_project_record(project_id)
    if not record:
        return None
    return ProjectState(
        project_id=str(record["id"]),
        name=str(record["name"]),
        request=str(record["request"]),
        status=str(record["status"]),
        root_path=str(record["root_path"]),
        workspace_path=str(Path(str(record["root_path"])) / "workspace"),
    )
