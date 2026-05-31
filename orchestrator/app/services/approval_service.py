from collections.abc import Mapping

from .. import db


def create_approval_record(
    project_id: str,
    approval_type: str,
    status: str,
    artifact_path: str,
    requested_by: str = "system",
    reason: str = "",
) -> Mapping[str, object]:
    return db.execute_returning(
        """
        INSERT INTO approvals (project_id, action, approval_type, status, artifact_path, requested_by, reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, project_id, action, approval_type, status, artifact_path, requested_by, reason, created_at, updated_at
        """,
        (project_id, approval_type, approval_type, status, artifact_path, requested_by, reason),
    )


def get_project_approvals(project_id: str) -> list[Mapping[str, object]]:
    return db.fetch_all(
        """
        SELECT id, action, approval_type, status, artifact_path, created_at, updated_at
        FROM approvals
        WHERE project_id = %s
        ORDER BY created_at ASC
        """,
        (project_id,),
    )


def get_approval_record(approval_id: str) -> Mapping[str, object] | None:
    return db.fetch_one(
        """
        SELECT id, project_id, action, approval_type, status, artifact_path, requested_by, reason, created_at, updated_at
        FROM approvals
        WHERE id = %s
        """,
        (approval_id,),
    )


def update_approval_status(
    approval_id: str,
    status: str,
    reason: str,
    validation_status: str | None = None,
    validation_artifact_path: str | None = None,
) -> Mapping[str, object]:
    return db.execute_returning(
        """
        UPDATE approvals
        SET status = %s,
            reason = %s,
            validation_status = COALESCE(%s, validation_status),
            validation_artifact_path = COALESCE(%s, validation_artifact_path),
            updated_at = now()
        WHERE id = %s
        RETURNING id, project_id, action, approval_type, status, artifact_path, requested_by, reason, created_at, updated_at
        """,
        (status, reason, validation_status, validation_artifact_path, approval_id),
    )
