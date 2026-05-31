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
