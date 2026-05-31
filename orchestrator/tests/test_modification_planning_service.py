import json
import uuid
from pathlib import Path

from orchestrator.app.schemas.modification_plan import ModificationPlanRequest
from orchestrator.app.services import modification_planning_service


def _project(root: Path, project_id: str) -> dict:
    return {
        "id": project_id,
        "name": "demo",
        "request": "Keep the service healthy",
        "status": "new",
        "root_path": str(root),
        "created_at": "now",
        "updated_at": "now",
    }


def _wire_db(monkeypatch, project: dict, approvals: list[dict] | None = None):
    records = approvals if approvals is not None else []
    events = []
    agent_runs = []

    monkeypatch.setattr(modification_planning_service, "get_project_record", lambda _project_id: project)
    monkeypatch.setattr(modification_planning_service, "record_event", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(modification_planning_service, "create_agent_run", lambda *args, **kwargs: agent_runs.append(args) or {})

    def fake_create_approval(project_id, approval_type, status, artifact_path, requested_by="system", reason=""):
        row = {
            "id": "approval-1",
            "project_id": project_id,
            "action": approval_type,
            "approval_type": approval_type,
            "status": status,
            "artifact_path": artifact_path,
            "requested_by": requested_by,
            "reason": reason,
            "created_at": "now",
            "updated_at": "now",
        }
        records.append(row)
        return row

    monkeypatch.setattr(modification_planning_service, "create_approval_record", fake_create_approval)
    monkeypatch.setattr(modification_planning_service, "get_project_approvals", lambda _project_id: records)
    return records, events, agent_runs


def test_modification_plan_blocks_when_runtime_inspection_missing(monkeypatch):
    project_id = str(uuid.uuid4())
    root = Path("test-output") / project_id / project_id
    (root / "qa").mkdir(parents=True)
    (root / "project-state.json").write_text("{}", encoding="utf-8")
    project = _project(root, project_id)
    records, events, agent_runs = _wire_db(monkeypatch, project)

    result = modification_planning_service.create_modification_plan(
        project_id,
        ModificationPlanRequest(change_request="Update service", target_type="systemd"),
    )

    assert result.status == "blocked"
    assert result.safe_to_modify is False
    assert "Runtime inspection evidence is missing." in result.blockers
    assert Path(result.plan_path).name == "blocked-modification-plan.md"
    assert (root / "approvals" / "blocked-modification-plan.json").exists()
    assert (root / "approvals" / "dry-run.patch").exists()
    assert records[0]["status"] == "blocked"
    assert events[0][2] == "modification_planning_started"
    assert agent_runs[0][1] == "modification_planner"
    assert agent_runs[0][4]["nothing_executed"] is True


def test_modification_plan_blocks_when_safe_to_modify_false(monkeypatch):
    project_id = str(uuid.uuid4())
    root = Path("test-output") / project_id / project_id
    (root / "qa").mkdir(parents=True)
    (root / "project-state.json").write_text("{}", encoding="utf-8")
    (root / "qa" / "runtime-inspection-evidence.json").write_text(
        json.dumps({"validation": {"safe_to_modify": False, "missing_requirements": ["Exact command"]}}),
        encoding="utf-8",
    )
    records, _, _ = _wire_db(monkeypatch, _project(root, project_id))

    result = modification_planning_service.create_modification_plan(
        project_id,
        ModificationPlanRequest(change_request="Update service", target_type="systemd"),
    )

    assert result.status == "blocked"
    assert result.blockers == ["Exact command"]
    assert records[0]["status"] == "blocked"


def test_modification_plan_pending_when_blockers_explicitly_allowed(monkeypatch):
    project_id = str(uuid.uuid4())
    root = Path("test-output") / project_id / project_id
    (root / "qa").mkdir(parents=True)
    (root / "project-state.json").write_text("{}", encoding="utf-8")
    (root / "qa" / "runtime-inspection-evidence.json").write_text(
        json.dumps({"validation": {"safe_to_modify": False, "missing_requirements": ["Exact command"]}}),
        encoding="utf-8",
    )
    records, _, _ = _wire_db(monkeypatch, _project(root, project_id))
    harness_dir = root.parents[1] / "harness" / "prod"
    registry_dir = root.parents[1] / "runtime" / "registries"
    harness_dir.mkdir(parents=True, exist_ok=True)
    registry_dir.mkdir(parents=True, exist_ok=True)
    harness_before = {path: path.read_bytes() for path in harness_dir.rglob("*") if path.is_file()}
    registry_before = {path: path.read_bytes() for path in registry_dir.rglob("*") if path.is_file()}

    result = modification_planning_service.create_modification_plan(
        project_id,
        ModificationPlanRequest(change_request="Update service", target_type="systemd", allow_plan_with_blockers=True),
    )

    assert result.status == "pending_approval"
    assert records[0]["status"] == "pending"
    assert (root / "approvals" / "modification-plan.md").exists()
    assert (root / "approvals" / "modification-plan.json").exists()
    assert "Candidate dry-run patch only" in (root / "approvals" / "dry-run.patch").read_text(encoding="utf-8")
    assert {path: path.read_bytes() for path in harness_dir.rglob("*") if path.is_file()} == harness_before
    assert {path: path.read_bytes() for path in registry_dir.rglob("*") if path.is_file()} == registry_before


def test_list_project_approvals_returns_records(monkeypatch):
    project_id = str(uuid.uuid4())
    root = Path("test-output") / project_id / project_id
    root.mkdir(parents=True)
    records = [
        {
            "id": "approval-1",
            "action": "modification_plan",
            "approval_type": "modification_plan",
            "status": "blocked",
            "artifact_path": str(root / "approvals" / "blocked-modification-plan.md"),
            "created_at": "now",
            "updated_at": "now",
        }
    ]
    _wire_db(monkeypatch, _project(root, project_id), records)

    result = modification_planning_service.list_project_approvals(project_id)

    assert result.approvals[0].approval_id == "approval-1"
    assert result.approvals[0].approval_type == "modification_plan"
