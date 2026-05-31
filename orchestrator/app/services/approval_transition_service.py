from collections.abc import Mapping

from ..schemas.approval_status import ApprovalStatusRequest, ApprovalStatusResponse
from .approval_service import get_approval_record, update_approval_status
from .project_service import get_project_record
from .run_service import record_event


class ApprovalTransitionError(ValueError):
    pass


def _response(row: Mapping[str, object]) -> ApprovalStatusResponse:
    return ApprovalStatusResponse(
        approval_id=str(row["id"]),
        project_id=str(row["project_id"]),
        approval_type=str(row.get("approval_type") or row.get("action") or ""),
        status=str(row["status"]),
        artifact_path=str(row.get("artifact_path") or ""),
        reason=str(row.get("reason") or ""),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def transition_approval_status(project_id: str, approval_id: str, request: ApprovalStatusRequest) -> ApprovalStatusResponse:
    project = get_project_record(project_id)
    if not project:
        raise KeyError(project_id)

    approval = get_approval_record(approval_id)
    if not approval or str(approval["project_id"]) != project_id:
        raise KeyError(approval_id)

    current = str(approval["status"])
    if current not in {"pending", "blocked"}:
        raise ApprovalTransitionError(f"Approval status can only transition from pending or blocked, not {current}.")
    if current == "blocked" and request.status == "approved" and not request.allow_blocked_approval:
        raise ApprovalTransitionError("Blocked approvals require allow_blocked_approval=true before approval.")

    record_event(
        project_id,
        None,
        "approval_status_transition_started",
        {
            "approval_id": approval_id,
            "from_status": current,
            "to_status": request.status,
            "reason": request.reason,
            "allow_blocked_approval": request.allow_blocked_approval,
            "nothing_executed": True,
        },
    )
    updated = update_approval_status(approval_id, request.status, request.reason)
    record_event(
        project_id,
        None,
        "approval_status_transition_completed",
        {
            "approval_id": approval_id,
            "from_status": current,
            "to_status": request.status,
            "reason": request.reason,
            "nothing_executed": True,
        },
    )
    return _response(updated)
