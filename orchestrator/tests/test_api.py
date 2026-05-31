import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from orchestrator.app import main
from orchestrator.app.schemas.project_state import ProjectState
from orchestrator.app.services.project_service import ProjectCreationError


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


def test_project_creation_failure_returns_json(monkeypatch):
    def fake_create_project(payload):
        raise ProjectCreationError("Project creation failed: relation tasks is missing", "project-1", "/srv/ai-lab/projects/project-1")

    monkeypatch.setattr(main, "create_project", fake_create_project)
    client = TestClient(main.app)
    response = client.post("/projects", json={"name": "demo", "request": "build a thing"})

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["detail"]["project_id"] == "project-1"
    assert "Project creation failed" in response.json()["detail"]["error"]


def test_llm_status_disabled(monkeypatch):
    monkeypatch.setattr(main.llm.settings, "ollama_enabled", False)
    client = TestClient(main.app)
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["provider"] == "ollama"
    assert response.json()["status"] == "disabled"
    assert response.json()["role_models"]["analyst"] == main.llm.settings.default_model


def test_llm_status_unreachable(monkeypatch):
    monkeypatch.setattr(main.llm.settings, "ollama_enabled", True)
    monkeypatch.setattr(main.llm.settings, "ollama_base_url", "http://127.0.0.1:9")
    client = TestClient(main.app)
    response = client.get("/llm/status")
    assert response.status_code == 200
    assert response.json()["status"] == "unreachable"
    assert "role_models" in response.json()


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


def test_runtime_inspect_endpoint(monkeypatch):
    monkeypatch.setattr(
        main,
        "run_runtime_inspection",
        lambda project_id, payload: {
            "project_id": project_id,
            "status": "complete",
            "runtime_inspection_report_path": "/srv/ai-lab/projects/project-1/qa/runtime-inspection-report.md",
            "task_packet_path": "/srv/ai-lab/projects/project-1/handoffs/runtime-inspector-task-packet.yaml",
            "agent_result_path": "/srv/ai-lab/projects/project-1/handoffs/runtime-inspector-agent-result.json",
            "inspection_summary": "Runtime inspection completed in read-only mode.",
            "blockers": ["Exact command"],
            "evidence": [{"kind": "project"}],
            "safe_to_modify": False,
        },
    )
    client = TestClient(main.app)
    response = client.post("/projects/project-1/runtime-inspect", json={"target_type": "unknown"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "project-1"
    assert payload["safe_to_modify"] is False
    assert payload["runtime_inspection_report_path"].endswith("runtime-inspection-report.md")


def assert_exists(root: Path, relative_path: str) -> None:
    assert (root / relative_path).exists(), relative_path
