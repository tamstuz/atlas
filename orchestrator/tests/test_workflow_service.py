import uuid
from pathlib import Path

from orchestrator.app.services import workflow_service


def test_workflow_run_creates_packets_results_and_final_report(monkeypatch):
    project_id = str(uuid.uuid4())
    test_root = Path("test-output") / project_id
    root = test_root / project_id
    (root / "handoffs").mkdir(parents=True)
    (root / "final").mkdir()
    (root / "project-state.json").write_text("{}", encoding="utf-8")
    (root / "decision-log.md").write_text("# Decision Log\n\n", encoding="utf-8")

    project = {
        "id": project_id,
        "name": "demo",
        "request": "Create a demo",
        "status": "new",
        "root_path": str(root),
        "created_at": "now",
        "updated_at": "now",
    }
    tasks = [
        {
            "id": f"task-{role}",
            "project_id": project_id,
            "title": f"{role} task",
            "status": "pending",
            "assigned_role": role,
            "phase": role,
            "started_at": None,
            "completed_at": None,
        }
        for role in workflow_service.DEFAULT_WORKFLOW_ROLES
    ]

    monkeypatch.setattr(workflow_service, "get_project_record", lambda _project_id: project)
    monkeypatch.setattr(workflow_service, "update_project_status", lambda _project_id, status: {**project, "status": status})
    monkeypatch.setattr(workflow_service, "get_project_tasks", lambda _project_id: tasks)
    monkeypatch.setattr(
        workflow_service,
        "get_task_for_role",
        lambda _project_id, role: next(task for task in tasks if task["assigned_role"] == role),
    )
    monkeypatch.setattr(workflow_service, "set_task_status", lambda task_id, status: None)
    monkeypatch.setattr(workflow_service, "create_agent_run", lambda *args, **kwargs: {})
    monkeypatch.setattr(workflow_service, "create_handoff", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow_service, "record_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow_service, "append_decision_for_project", lambda *args, **kwargs: None)
    monkeypatch.setattr(workflow_service, "write_project_files", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        workflow_service,
        "load_role_bundle",
        lambda role: {"role": role, "files": [{"path": str(test_root / f"{role}.md"), "content": "role"}]},
    )

    result = workflow_service.run_project_workflow(project_id)

    assert result["status"] == "complete"
    for index, role in enumerate(workflow_service.DEFAULT_WORKFLOW_ROLES, start=1):
        prefix = f"{index:02d}-{role}"
        assert (root / "handoffs" / f"{prefix}-task-packet.yaml").exists()
        assert (root / "handoffs" / f"{prefix}-agent-result.json").exists()
    assert Path(result["final_report_path"]).exists()
