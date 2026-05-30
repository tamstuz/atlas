from collections.abc import Mapping

from psycopg.types.json import Jsonb

from .. import db


def create_agent_run(task_id: str, role: str, status: str, input_data: dict, output_data: dict) -> Mapping[str, object]:
    return db.execute_returning(
        """
        INSERT INTO agent_runs (task_id, agent_role, status, input, output)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, task_id, agent_role, status, created_at
        """,
        (task_id, role, status, Jsonb(input_data), Jsonb(output_data)),
    )


def create_handoff(task_id: str, from_role: str, to_role: str, packet: dict) -> None:
    db.execute(
        """
        INSERT INTO handoffs (task_id, from_role, to_role, status, packet)
        VALUES (%s, %s, %s, 'complete', %s)
        """,
        (task_id, from_role, to_role, Jsonb(packet)),
    )


def record_event(project_id: str, task_id: str | None, event_type: str, payload: dict, status: str = "recorded") -> None:
    db.execute(
        """
        INSERT INTO events (project_id, task_id, event_type, payload, status)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (project_id, task_id, event_type, Jsonb(payload), status),
    )
