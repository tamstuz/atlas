import json
from pathlib import Path

from orchestrator.app.schemas.change_package import ChangePackageRequest
from orchestrator.app.services import change_package_service
from orchestrator.app.services.command_classification_service import classify_human_command


def _project(root: Path) -> dict:
    return {
        "id": "project-1",
        "name": "demo",
        "request": "Package a safe production change",
        "status": "new",
        "root_path": str(root),
        "created_at": "now",
        "updated_at": "now",
    }


def _approval(root: Path, status: str = "approved") -> dict:
    return {
        "id": "approval-1",
        "project_id": "project-1",
        "action": "modification_plan",
        "approval_type": "modification_plan",
        "status": status,
        "artifact_path": str(root / "approvals" / "modification-plan.md"),
        "requested_by": "system",
        "reason": "",
        "created_at": "now",
        "updated_at": "now",
    }


def _write_valid_sources(root: Path, commands: list[str] | None = None, dry_status: str = "passed", sandbox_status: str = "passed") -> None:
    approvals = root / "approvals"
    sandbox = root / "sandbox"
    approvals.mkdir(parents=True, exist_ok=True)
    sandbox.mkdir(parents=True, exist_ok=True)
    (approvals / "modification-plan.md").write_text("# Candidate Modification Plan\n", encoding="utf-8")
    (approvals / "modification-plan.json").write_text(
        json.dumps(
            {
                "change_request": "Update demo config",
                "target_type": "file",
                "target_hint": "workspace/app.conf",
                "runtime_inspection_source": str(root / "qa" / "runtime-inspection-evidence.json"),
                "evidence_backed_facts": ["Dry-run and sandbox validation passed."],
                "inferences": ["Human execution can be reviewed from this package."],
                "unknowns": [],
                "blocked_items": [],
                "risk_rating": "medium",
                "proposed_files_to_change": ["workspace/app.conf"],
                "proposed_commands": commands or ["bash -n install.sh"],
            }
        ),
        encoding="utf-8",
    )
    (approvals / "dry-run.patch").write_text("# dry-run only\n", encoding="utf-8")
    (approvals / "dry-run-validation-result.json").write_text(json.dumps({"status": dry_status}), encoding="utf-8")
    (approvals / "patch-validation.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")
    (sandbox / "sandbox-run-result.json").write_text(json.dumps({"status": sandbox_status}), encoding="utf-8")
    (sandbox / "sandbox-run-report.md").write_text("# Sandbox Run Report\n", encoding="utf-8")
    (sandbox / "sandbox-file-manifest.json").write_text(json.dumps({"workspace_files": []}), encoding="utf-8")
    (sandbox / "sandbox-command-log.json").write_text(json.dumps({"commands_executed": []}), encoding="utf-8")


def _wire(monkeypatch, root: Path, approval_status: str = "approved"):
    events = []
    approvals = []
    monkeypatch.setattr(change_package_service, "get_project_record", lambda _project_id: _project(root))
    monkeypatch.setattr(change_package_service, "get_approval_record", lambda _approval_id: _approval(root, approval_status))
    monkeypatch.setattr(change_package_service, "record_event", lambda *args, **kwargs: events.append((args, kwargs)))
    monkeypatch.setattr(
        change_package_service,
        "create_approval_record",
        lambda *args, **kwargs: approvals.append((args, kwargs))
        or {
            "id": "final-approval-1",
            "project_id": "project-1",
            "approval_type": "production_change_package",
            "status": "pending",
            "artifact_path": str(root / "change-package" / "production-change-package.md"),
            "created_at": "now",
            "updated_at": "now",
        },
    )
    return events, approvals


def test_change_package_requires_approved_approval(monkeypatch, tmp_path):
    _write_valid_sources(tmp_path)
    _wire(monkeypatch, tmp_path, approval_status="pending")

    result = change_package_service.generate_change_package("project-1", "approval-1", ChangePackageRequest())

    assert result.status == "blocked"
    assert "approval status approved" in result.issues[0]
    assert not (tmp_path / "change-package" / "production-change-package.md").exists()


def test_change_package_requires_dry_run_validation_passed(monkeypatch, tmp_path):
    _write_valid_sources(tmp_path, dry_status="failed")
    _wire(monkeypatch, tmp_path)

    result = change_package_service.generate_change_package("project-1", "approval-1", ChangePackageRequest())

    assert result.status == "blocked"
    assert any("dry-run validation status passed" in issue for issue in result.issues)


def test_change_package_requires_sandbox_validation_passed(monkeypatch, tmp_path):
    _write_valid_sources(tmp_path, sandbox_status="failed")
    _wire(monkeypatch, tmp_path)

    result = change_package_service.generate_change_package("project-1", "approval-1", ChangePackageRequest())

    assert result.status == "blocked"
    assert any("sandbox validation status passed" in issue for issue in result.issues)


def test_change_package_writes_required_artifacts_and_copies_sources(monkeypatch, tmp_path):
    _write_valid_sources(tmp_path, commands=["sudo systemctl restart demo"])
    harness_prod = tmp_path / "harness" / "prod"
    registries = tmp_path / "runtime" / "registries"
    harness_prod.mkdir(parents=True)
    registries.mkdir(parents=True)
    (harness_prod / "policy.md").write_text("original", encoding="utf-8")
    (registries / "service-registry.yaml").write_text("original", encoding="utf-8")
    events, approvals = _wire(monkeypatch, tmp_path)

    result = change_package_service.generate_change_package(
        "project-1",
        "approval-1",
        ChangePackageRequest(change_window="Sunday 01:00 UTC", operator="ops", notes="review only"),
    )

    package = tmp_path / "change-package"
    assert result.status == "packaged"
    assert (package / "production-change-package.md").exists()
    assert (package / "production-change-package.json").exists()
    assert (package / "human-execution-checklist.md").exists()
    assert (package / "exact-command-plan.md").exists()
    assert (package / "rollback-checklist.md").exists()
    assert (package / "preflight-checklist.md").exists()
    assert (package / "postchange-checklist.md").exists()
    assert (package / "final-approval-request.json").exists()
    assert (package / "source-artifact-manifest.json").exists()
    assert (package / "source" / "modification-plan.md").exists()
    assert (package / "source" / "dry-run-validation-result.json").exists()
    assert (package / "source" / "sandbox-run-result.json").exists()
    assert result.final_approval_id == "final-approval-1"
    assert approvals[0][0][1] == "production_change_package"
    assert approvals[0][0][2] == "pending"
    assert result.production_modified is False
    assert result.global_registries_modified is False
    assert result.harness_modified is False
    assert (harness_prod / "policy.md").read_text(encoding="utf-8") == "original"
    assert (registries / "service-registry.yaml").read_text(encoding="utf-8") == "original"
    assert [event[0][2] for event in events] == [
        "change_package_started",
        "change_package_sources_loaded",
        "final_approval_created",
        "change_package_generated",
    ]


def test_exact_command_plan_is_human_only_and_not_executed(monkeypatch, tmp_path):
    _write_valid_sources(tmp_path, commands=["sudo systemctl restart demo"])
    _wire(monkeypatch, tmp_path)

    change_package_service.generate_change_package("project-1", "approval-1", ChangePackageRequest())

    payload = json.loads((tmp_path / "change-package" / "production-change-package.json").read_text(encoding="utf-8"))
    command = payload["command_classification"]["commands"][0]
    assert command["human_only"] is True
    assert command["blocked_for_agent"] is True
    assert payload["command_classification"]["commands_executed"] is False
    assert "blocked_for_agent" in command["classification"]


def test_dangerous_commands_are_blocked_for_agent_and_human_only():
    result = classify_human_command("rm /srv/ai-lab/projects/demo/file")

    assert result["human_only"] is True
    assert result["blocked_for_agent"] is True
    assert "blocked_for_agent" in result["classification"]


def test_list_change_packages_returns_package_records(monkeypatch, tmp_path):
    monkeypatch.setattr(change_package_service, "get_project_record", lambda _project_id: _project(tmp_path))
    monkeypatch.setattr(
        change_package_service.db,
        "fetch_all",
        lambda *args, **kwargs: [
            {
                "id": "final-approval-1",
                "source_approval_id": "approval-1",
                "status": "pending",
                "artifact_path": str(tmp_path / "change-package" / "production-change-package.md"),
                "created_at": "created",
                "updated_at": "updated",
            }
        ],
    )

    result = change_package_service.list_change_packages("project-1")

    assert result.project_id == "project-1"
    assert result.change_packages[0].approval_id == "approval-1"
    assert result.change_packages[0].final_approval_id == "final-approval-1"
