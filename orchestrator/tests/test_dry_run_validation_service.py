import json
from pathlib import Path

import pytest

from orchestrator.app.schemas.approval_status import DryRunValidationRequest
from orchestrator.app.services import dry_run_validation_service
from orchestrator.app.services.command_plan_validator import classify_command
from orchestrator.app.services.dry_run_validation_service import DryRunValidationError, validate_rollback_plan
from orchestrator.app.services.patch_validation_service import validate_patch


def _project(root: Path) -> dict:
    return {
        "id": "project-1",
        "name": "demo",
        "request": "Change safely",
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


def _write_plan(root: Path, commands: list[str] | None = None, rollback_plan=None) -> None:
    approvals = root / "approvals"
    approvals.mkdir(parents=True, exist_ok=True)
    (approvals / "modification-plan.md").write_text("# Candidate Modification Plan\n", encoding="utf-8")
    (approvals / "modification-plan.json").write_text(
        json.dumps(
            {
                "approval_status": "pending_approval",
                "proposed_commands": commands or [],
                "rollback_plan": rollback_plan
                or {
                    "files affected": ["workspace/app.py"],
                    "backup strategy": "Copy original file under approvals before future execution.",
                    "restore steps": "Restore the original file from the backup.",
                    "verification after rollback": "Run the approved validation checks.",
                    "failure trigger": "Any failed validation check.",
                    "owner/human approval requirement": "Human approval required before rollback execution.",
                },
            }
        ),
        encoding="utf-8",
    )
    (approvals / "dry-run.patch").write_text(
        "\n".join(
            [
                "diff --git a/workspace/app.py b/workspace/app.py",
                "--- a/workspace/app.py",
                "+++ b/workspace/app.py",
                "@@ -1 +1 @@",
                "-old",
                "+new",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _wire(monkeypatch, root: Path, approval_status: str = "approved"):
    events = []
    updates = []
    monkeypatch.setattr(dry_run_validation_service, "get_project_record", lambda _project_id: _project(root))
    monkeypatch.setattr(dry_run_validation_service, "get_approval_record", lambda _approval_id: _approval(root, approval_status))
    monkeypatch.setattr(dry_run_validation_service, "record_event", lambda *args, **kwargs: events.append(args))
    monkeypatch.setattr(
        dry_run_validation_service,
        "update_approval_status",
        lambda *args, **kwargs: updates.append(args) or _approval(root, approval_status),
    )
    return events, updates


def test_dry_run_requires_approved_status(monkeypatch, tmp_path):
    _write_plan(tmp_path)
    _wire(monkeypatch, tmp_path, approval_status="pending")

    with pytest.raises(DryRunValidationError):
        dry_run_validation_service.run_dry_run_validation(
            "project-1",
            "approval-1",
            DryRunValidationRequest(),
        )


def test_dry_run_validation_writes_artifacts_and_does_not_mutate_global_paths(monkeypatch, tmp_path):
    _write_plan(tmp_path)
    harness_prod = tmp_path / "harness" / "prod"
    registries = tmp_path / "runtime" / "registries"
    harness_prod.mkdir(parents=True)
    registries.mkdir(parents=True)
    (harness_prod / "policy.md").write_text("original", encoding="utf-8")
    (registries / "service-registry.yaml").write_text("original", encoding="utf-8")
    harness_before = (harness_prod / "policy.md").read_text(encoding="utf-8")
    registry_before = (registries / "service-registry.yaml").read_text(encoding="utf-8")
    events, updates = _wire(monkeypatch, tmp_path)

    result = dry_run_validation_service.run_dry_run_validation(
        "project-1",
        "approval-1",
        DryRunValidationRequest(validation_mode="full_dry_run"),
    )

    assert result.status == "passed"
    assert (tmp_path / "approvals" / "dry-run-validation-report.md").exists()
    assert (tmp_path / "approvals" / "dry-run-validation-result.json").exists()
    assert (tmp_path / "approvals" / "patch-validation.json").exists()
    assert result.production_modified is False
    assert result.global_registries_modified is False
    assert result.harness_modified is False
    assert (harness_prod / "policy.md").read_text(encoding="utf-8") == harness_before
    assert (registries / "service-registry.yaml").read_text(encoding="utf-8") == registry_before
    assert events[0][2] == "dry_run_validation_started"
    assert events[1][2] == "dry_run_validation_completed"
    assert updates[0][3] == "passed"


def test_forbidden_patch_targets_are_blocked(tmp_path):
    patch = tmp_path / "approvals" / "dry-run.patch"
    patch.parent.mkdir(parents=True)
    patch.write_text(
        "diff --git a/etc/systemd/system/demo.service b/etc/systemd/system/demo.service\n"
        "--- a/etc/systemd/system/demo.service\n"
        "+++ b/etc/systemd/system/demo.service\n",
        encoding="utf-8",
    )

    result = validate_patch(patch, tmp_path)

    assert result["status"] == "blocked"
    assert any("Forbidden patch target" in issue for issue in result["issues"])


def test_project_local_absolute_patch_targets_are_allowed(tmp_path):
    patch = tmp_path / "approvals" / "dry-run.patch"
    patch.parent.mkdir(parents=True)
    target = f"{tmp_path.as_posix().lstrip('/')}/workspace/app.py"
    patch.write_text(
        f"diff --git a/{target} b/{target}\n"
        f"--- a/{target}\n"
        f"+++ b/{target}\n",
        encoding="utf-8",
    )

    result = validate_patch(patch, tmp_path)

    assert result["status"] == "passed"


def test_harness_prod_patch_targets_are_blocked(tmp_path):
    patch = tmp_path / "approvals" / "dry-run.patch"
    patch.parent.mkdir(parents=True)
    patch.write_text(
        "diff --git a/srv/ai-lab/harness/prod/00_READ_FIRST.md b/srv/ai-lab/harness/prod/00_READ_FIRST.md\n",
        encoding="utf-8",
    )

    result = validate_patch(patch, tmp_path)

    assert result["status"] == "blocked"


def test_global_registry_patch_targets_are_blocked(tmp_path):
    patch = tmp_path / "approvals" / "dry-run.patch"
    patch.parent.mkdir(parents=True)
    patch.write_text(
        "diff --git a/srv/ai-lab/runtime/registries/service-registry.yaml b/srv/ai-lab/runtime/registries/service-registry.yaml\n",
        encoding="utf-8",
    )

    result = validate_patch(patch, tmp_path)

    assert result["status"] == "blocked"


def test_sudo_and_service_restart_commands_are_blocked():
    assert classify_command("sudo systemctl restart demo")["classification"] == "blocked"
    assert classify_command("systemctl restart demo")["classification"] == "blocked"


def test_rollback_plan_validation_detects_missing_items():
    result = validate_rollback_plan({"rollback_plan": "Restore the file."})

    assert result["rollback_plan_present"] is True
    assert result["rollback_plan_complete"] is False
    assert "files affected" in result["missing_rollback_items"]


def test_dry_run_blocks_forbidden_patch_without_applying_or_executing(monkeypatch, tmp_path):
    _write_plan(tmp_path, commands=["sudo systemctl restart demo"])
    (tmp_path / "approvals" / "dry-run.patch").write_text(
        "diff --git a/srv/ai-lab/harness/prod/00_READ_FIRST.md b/srv/ai-lab/harness/prod/00_READ_FIRST.md\n",
        encoding="utf-8",
    )
    _wire(monkeypatch, tmp_path)

    result = dry_run_validation_service.run_dry_run_validation(
        "project-1",
        "approval-1",
        DryRunValidationRequest(),
    )

    payload = json.loads((tmp_path / "approvals" / "dry-run-validation-result.json").read_text(encoding="utf-8"))
    assert result.status == "blocked"
    assert payload["patch_validation"]["patch_applied"] is False
    assert payload["command_validation"]["commands_executed"] is False
