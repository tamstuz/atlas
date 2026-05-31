import pytest

from orchestrator.app.schemas.approval_status import ApprovalStatusRequest
from orchestrator.app.services import approval_transition_service
from orchestrator.app.services.approval_transition_service import ApprovalTransitionError


def _approval(status: str) -> dict:
    return {
        "id": "approval-1",
        "project_id": "project-1",
        "action": "modification_plan",
        "approval_type": "modification_plan",
        "status": status,
        "artifact_path": "/srv/ai-lab/projects/project-1/approvals/modification-plan.md",
        "requested_by": "system",
        "reason": "",
        "created_at": "now",
        "updated_at": "now",
    }


def _wire(monkeypatch, approval: dict):
    events = []
    monkeypatch.setattr(approval_transition_service, "get_project_record", lambda project_id: {"id": project_id})
    monkeypatch.setattr(approval_transition_service, "get_approval_record", lambda _approval_id: approval)
    monkeypatch.setattr(approval_transition_service, "record_event", lambda *args, **kwargs: events.append(args))

    def fake_update(_approval_id, status, reason, validation_status=None, validation_artifact_path=None):
        approval["status"] = status
        approval["reason"] = reason
        return approval

    monkeypatch.setattr(approval_transition_service, "update_approval_status", fake_update)
    return events


def test_pending_approval_can_be_approved(monkeypatch):
    approval = _approval("pending")
    events = _wire(monkeypatch, approval)

    result = approval_transition_service.transition_approval_status(
        "project-1",
        "approval-1",
        ApprovalStatusRequest(status="approved", reason="Reviewed by human."),
    )

    assert result.status == "approved"
    assert result.reason == "Reviewed by human."
    assert events[0][2] == "approval_status_transition_started"
    assert events[1][2] == "approval_status_transition_completed"


def test_pending_approval_can_be_rejected(monkeypatch):
    approval = _approval("pending")
    _wire(monkeypatch, approval)

    result = approval_transition_service.transition_approval_status(
        "project-1",
        "approval-1",
        ApprovalStatusRequest(status="rejected", reason="Too risky."),
    )

    assert result.status == "rejected"


def test_blocked_approval_requires_explicit_allow_before_approval(monkeypatch):
    approval = _approval("blocked")
    _wire(monkeypatch, approval)

    with pytest.raises(ApprovalTransitionError):
        approval_transition_service.transition_approval_status(
            "project-1",
            "approval-1",
            ApprovalStatusRequest(status="approved", reason="Override requested."),
        )


def test_blocked_approval_can_be_approved_when_explicitly_allowed(monkeypatch):
    approval = _approval("blocked")
    _wire(monkeypatch, approval)

    result = approval_transition_service.transition_approval_status(
        "project-1",
        "approval-1",
        ApprovalStatusRequest(status="approved", reason="Override approved.", allow_blocked_approval=True),
    )

    assert result.status == "approved"
