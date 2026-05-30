from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from .config import settings


class DatabaseUnavailable(RuntimeError):
    pass


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    try:
        with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=3) as conn:
            yield conn
    except psycopg.OperationalError as exc:
        raise DatabaseUnavailable(f"PostgreSQL is unreachable: {exc}") from exc


def fetch_one(sql: str, params: Sequence[object] = ()) -> Mapping[str, object] | None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def fetch_all(sql: str, params: Sequence[object] = ()) -> list[Mapping[str, object]]:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return list(cur.fetchall())


def execute(sql: str, params: Sequence[object] = ()) -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def execute_returning(sql: str, params: Sequence[object] = ()) -> Mapping[str, object]:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("Expected database statement to return a row.")
            return row
