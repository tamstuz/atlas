import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from orchestrator.app import main
from orchestrator.app.schemas.project_state import ProjectState


def test_health_endpoint():
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_project_creation_endpoint(monkeypatch):
    root = Path("test-output") / str(uuid.uuid4())

    def fake_create_project(payload):
        return ProjectState(
            project_id="project-1",
            name=payload.name,
            request=payload.request,
            status="new",
            root_path=str(root),
            workspace_path=str(root / "workspace"),
        )

    monkeypatch.setattr(main, "create_project", fake_create_project)
    client = TestClient(main.app)
    response = client.post("/projects", json={"name": "demo", "request": "build a thing"})
    assert response.status_code == 200
    assert response.json()["project_id"] == "project-1"


def test_llm_status_disabled(monkeypatch):
    monkeypatch.setattr(main.llm.settings, "ollama_enabled", False)
    client = TestClient(main.app)
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json() == {"enabled": False, "provider": "ollama", "status": "disabled"}


def test_llm_status_unreachable(monkeypatch):
    monkeypatch.setattr(main.llm.settings, "ollama_enabled", True)
    monkeypatch.setattr(main.llm.settings, "ollama_base_url", "http://127.0.0.1:9")
    client = TestClient(main.app)
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json()["status"] == "unreachable"


def test_workflow_run_endpoint(monkeypatch):
    monkeypatch.setattr(
        main,
        "run_project_workflow",
        lambda project_id: {
            "project_id": project_id,
            "thread_id": project_id,
            "status": "complete",
            "workflow": ["intake"],
            "artifacts_created": [],
            "final_report_path": "/tmp/final-report.md",
        },
    )
    client = TestClient(main.app)
    response = client.post("/projects/project-1/run")
    assert response.status_code == 200
    assert response.json()["status"] == "complete"


def assert_exists(root: Path, relative_path: str) -> None:
    assert (root / relative_path).exists(), relative_path
