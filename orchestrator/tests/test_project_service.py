import uuid
from contextlib import contextmanager
from pathlib import Path

from orchestrator.app import db
from orchestrator.app.schemas.project_state import ProjectCreate
from orchestrator.app.services import project_service


def test_project_creation_db_failure_records_partial_state(monkeypatch):
    project_root = Path("test-output") / str(uuid.uuid4())
    monkeypatch.setattr(project_service.settings, "projects_dir", project_root)

    @contextmanager
    def failing_connection():
        raise db.DatabaseUnavailable("PostgreSQL is unreachable: test")
        yield

    monkeypatch.setattr(project_service.db, "connection", failing_connection)

    try:
        project_service.create_project(ProjectCreate(name="demo", request="build a thing"))
    except project_service.ProjectCreationError as exc:
        assert exc.project_id is not None
        partial_root = project_root / exc.project_id
        assert (partial_root / "project-state.json").exists()
        state = (partial_root / "project-state.json").read_text(encoding="utf-8")
        assert '"status": "failed"' in state
        assert "PostgreSQL is unreachable" in state
    else:
        raise AssertionError("Expected ProjectCreationError")
