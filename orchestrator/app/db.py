import logging
from collections.abc import Mapping

import psycopg
from psycopg.rows import dict_row

from .config import settings

logger = logging.getLogger(__name__)


def create_project_record(project_id: str, name: str, request: str, root_path: str) -> None:
    sql = """
        INSERT INTO projects (id, name, request, root_path, status)
        VALUES (%s, %s, %s, %s, 'new')
        ON CONFLICT (id) DO NOTHING
    """
    try:
        with psycopg.connect(settings.database_url, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (project_id, name, request, root_path))
    except Exception as exc:  # pragma: no cover - DB can be unavailable in local scaffold tests.
        logger.warning("Project record was not written to PostgreSQL: %s", exc)


def get_project_record(project_id: str) -> Mapping[str, object] | None:
    sql = "SELECT id, name, request, status, root_path, created_at, updated_at FROM projects WHERE id = %s"
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (project_id,))
                return cur.fetchone()
    except Exception as exc:  # pragma: no cover
        logger.warning("Project record was not read from PostgreSQL: %s", exc)
        return None
