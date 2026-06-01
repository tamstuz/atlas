import json
from pathlib import Path

import pytest

from orchestrator.app.schemas.sandbox_run import SandboxRunRequest
from orchestrator.app.services import sandbox_command_service, sandbox_service
from orchestrator.app.services.sandbox_command_service import classify_sandbox_command
from orchestrator.app.services.sandbox_service import SandboxRunError


def _project(root: Path) -> dict:
    return {
        "id": "project-1",
        "name": "demo",
        "request": "Validate in sandbox",
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


def _write_approved_artifacts(root: Path, commands: list[str] | None = None, patch_text: str | None = None, dry_run_status: str = "passed") -> None:
    approvals = root / "approvals"
    approvals.mkdir(parents=True, exist_ok=True)
    (approvals / "modification-plan.md").write_text("# Candidate Modification Plan\n", encoding="utf-8")
    (approvals / "modification-plan.json").write_text(json.dumps({"proposed_commands": commands or []}), encoding="utf-8")
    (approvals / "dry-run.patch").write_text(
        patch_text
        if patch_text is not None
        else "\n".join(
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
    (approvals / "dry-run-validation-result.json").write_text(json.dumps({"status": dry_run_status}), encoding="utf-8")
    (approvals / "patch-validation.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")


def _wire(monkeypatch, root: Path, approval_status: str = "approved"):
    events = []
    monkeypatch.setattr(sandbox_service, "get_project_record", lambda _project_id: _project(root))
    monkeypatch.setattr(sandbox_service, "get_approval_record", lambda _approval_id: _approval(root, approval_status))
    monkeypatch.setattr(sandbox_service, "record_event", lambda *args, **kwargs: events.append(args))
    return events


def test_sandbox_run_requires_approved_approval(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path)
    _wire(monkeypatch, tmp_path, approval_status="pending")

    with pytest.raises(SandboxRunError):
        sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())


def test_sandbox_run_requires_prior_dry_run_passed(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path, dry_run_status="failed")
    _wire(monkeypatch, tmp_path)

    with pytest.raises(SandboxRunError):
        sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())


def test_sandbox_run_creates_project_sandbox_and_copies_artifacts(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path)
    events = _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())

    sandbox = tmp_path / "sandbox"
    assert result.status == "passed"
    assert Path(result.sandbox_path) == sandbox
    assert (sandbox / "input" / "modification-plan.md").exists()
    assert (sandbox / "input" / "modification-plan.json").exists()
    assert (sandbox / "input" / "dry-run.patch").exists()
    assert (sandbox / "input" / "dry-run-validation-result.json").exists()
    assert (sandbox / "input" / "patch-validation.json").exists()
    assert (sandbox / "sandbox-run-report.md").exists()
    assert (sandbox / "sandbox-run-result.json").exists()
    assert (sandbox / "sandbox-command-log.json").exists()
    assert (sandbox / "sandbox-file-manifest.json").exists()
    assert (sandbox / "applied.patch").exists()
    assert (sandbox / "workspace" / "app.py").read_text(encoding="utf-8") == "new\n"
    assert events[0][2] == "sandbox_run_started"
    assert events[-1][2] == "sandbox_run_completed"


def test_patch_is_not_applied_to_production(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path)
    production_file = tmp_path / "workspace" / "app.py"
    production_file.parent.mkdir(parents=True)
    production_file.write_text("old\n", encoding="utf-8")
    _wire(monkeypatch, tmp_path)

    sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())

    assert production_file.read_text(encoding="utf-8") == "old\n"


def test_forbidden_patch_targets_are_blocked(monkeypatch, tmp_path):
    _write_approved_artifacts(
        tmp_path,
        patch_text="diff --git a/srv/ai-lab/runtime/registries/service-registry.yaml b/srv/ai-lab/runtime/registries/service-registry.yaml\n",
    )
    _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())

    assert result.status == "blocked"
    assert any("Forbidden patch target" in issue for issue in result.issues)


def test_path_traversal_is_blocked(monkeypatch, tmp_path):
    _write_approved_artifacts(
        tmp_path,
        patch_text="\n".join(
            [
                "diff --git a/workspace/../escape.txt b/workspace/../escape.txt",
                "--- a/workspace/../escape.txt",
                "+++ b/workspace/../escape.txt",
                "@@ -0,0 +1 @@",
                "+escape",
                "",
            ]
        ),
    )
    _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())

    assert result.status == "blocked"
    assert any("escapes sandbox workspace" in issue for issue in result.issues)


def test_harness_prod_mutation_is_blocked(monkeypatch, tmp_path):
    _write_approved_artifacts(
        tmp_path,
        patch_text="diff --git a/srv/ai-lab/harness/prod/00_READ_FIRST.md b/srv/ai-lab/harness/prod/00_READ_FIRST.md\n",
    )
    _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest())

    assert result.status == "blocked"


def test_no_sudo_or_production_system_command_execution(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path, commands=["sudo systemctl restart demo", "systemctl restart demo"])
    _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest(sandbox_mode="plan_only"))

    assert result.status == "blocked"
    assert len(result.commands_executed) == 0
    assert len(result.commands_blocked) == 2


def test_commands_are_not_executed_when_disabled(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path, commands=["pwd"])
    _wire(monkeypatch, tmp_path)

    result = sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest(sandbox_mode="plan_only"))

    assert result.status == "passed"
    assert len(result.commands_executed) == 0
    assert result.commands_blocked[0]["classification"] == "not_executed"


def test_blocked_commands_are_recorded(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path, commands=["curl http://example.com"])
    _wire(monkeypatch, tmp_path)

    sandbox_service.run_sandbox("project-1", "approval-1", SandboxRunRequest(sandbox_mode="plan_only"))
    command_log = json.loads((tmp_path / "sandbox" / "sandbox-command-log.json").read_text(encoding="utf-8"))

    assert command_log["commands_blocked"][0]["command"] == "curl http://example.com"


def test_safe_sandbox_command_runs_only_when_enabled(monkeypatch, tmp_path):
    _write_approved_artifacts(tmp_path, commands=["pwd"])
    _wire(monkeypatch, tmp_path)

    class Completed:
        returncode = 0
        stdout = "sandbox\n"
        stderr = ""

    calls = []
    monkeypatch.setattr(
        sandbox_command_service.subprocess,
        "run",
        lambda *args, **kwargs: calls.append((args, kwargs)) or Completed(),
    )

    result = sandbox_service.run_sandbox(
        "project-1",
        "approval-1",
        SandboxRunRequest(sandbox_mode="plan_only", allow_sandbox_commands=True),
    )

    assert result.status == "passed"
    assert len(result.commands_executed) == 1
    assert calls[0][1]["cwd"] == tmp_path / "sandbox"
    assert calls[0][1]["shell"] is not True if "shell" in calls[0][1] else True


def test_sandbox_command_classifier_blocks_live_mutation_commands():
    assert classify_sandbox_command("sudo whoami")["classification"] == "blocked"
    assert classify_sandbox_command("docker run alpine")["classification"] == "blocked"
    assert classify_sandbox_command("bash -n install.sh")["classification"] == "allowed_sandbox"
