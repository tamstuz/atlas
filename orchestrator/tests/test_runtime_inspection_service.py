import uuid
from pathlib import Path

from orchestrator.app.services import runtime_inspection_service
from orchestrator.app.schemas.runtime_inspection import RuntimeInspectRequest


def test_runtime_inspection_creates_artifacts_and_records(monkeypatch):
    project_id = str(uuid.uuid4())
    test_root = Path("test-output") / project_id
    root = test_root / project_id
    (root / "handoffs").mkdir(parents=True)
    (root / "qa").mkdir()
    (root / "project-state.json").write_text("{}", encoding="utf-8")
    (root / "decision-log.md").write_text("# Decision Log\n\n", encoding="utf-8")

    project = {
        "id": project_id,
        "name": "demo",
        "request": "Find the real service entrypoint",
        "status": "new",
        "root_path": str(root),
        "created_at": "now",
        "updated_at": "now",
    }
    task = {
        "id": "task-runtime-inspector",
        "project_id": project_id,
        "title": "runtime_inspector task",
        "status": "pending",
        "assigned_role": "runtime_inspector",
        "phase": "runtime_inspection",
        "started_at": None,
        "completed_at": None,
    }
    statuses = []
    agent_runs = []
    events = []

    harness_dir = test_root / "harness" / "prod"
    harness_dir.mkdir(parents=True)
    harness_before = {path: path.read_bytes() for path in harness_dir.rglob("*") if path.is_file()}

    monkeypatch.setattr(runtime_inspection_service, "get_project_record", lambda _project_id: project)
    monkeypatch.setattr(runtime_inspection_service, "get_task_for_role", lambda _project_id, role: task)
    monkeypatch.setattr(runtime_inspection_service, "set_task_status", lambda task_id, status: statuses.append(status))
    monkeypatch.setattr(runtime_inspection_service, "create_agent_run", lambda *args, **kwargs: agent_runs.append(args) or {})
    monkeypatch.setattr(runtime_inspection_service, "create_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(runtime_inspection_service, "record_event", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(runtime_inspection_service, "append_decision_for_project", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        runtime_inspection_service,
        "load_role_bundle",
        lambda role: {
            "role": role,
            "files": [
                {"path": str(harness_dir / "roles" / "runtime-inspector.md"), "content": "runtime inspector"},
                {"path": str(harness_dir / "runtime-control" / "discover-before-modify.md"), "content": "policy"},
            ],
        },
    )
    monkeypatch.setattr(runtime_inspection_service.settings, "runtime_inspection_commands_enabled", False)

    result = runtime_inspection_service.run_runtime_inspection(
        project_id,
        RuntimeInspectRequest(target_type="systemd", target_hint="demo.service", allow_read_only_commands=True),
    )

    assert result.status == "complete"
    assert result.safe_to_modify is False
    assert statuses == ["running", "complete"]
    assert agent_runs
    assert events[0][2] == "runtime_inspection_started"
    assert (root / "handoffs" / "runtime-inspector-task-packet.yaml").exists()
    assert (root / "handoffs" / "runtime-inspector-agent-result.json").exists()
    assert (root / "qa" / "runtime-inspection-report.md").exists()
    assert (root / "qa" / "runtime-inspection-evidence.json").exists()
    assert (root / "qa" / "candidate-runtime-registry-updates.yaml").exists()
    assert {path: path.read_bytes() for path in harness_dir.rglob("*") if path.is_file()} == harness_before
