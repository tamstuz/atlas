from pathlib import Path


def test_v02_migration_adds_required_task_columns():
    migration = Path("../db/migrations/002-v0.2-db-backed-orchestration.sql").read_text(encoding="utf-8")

    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS phase TEXT" in migration
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ" in migration
    assert "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ" in migration
    assert "ALTER TABLE tasks ALTER COLUMN status SET DEFAULT 'pending'" in migration
    assert "UPDATE tasks SET status = 'pending' WHERE status = 'new'" in migration


def test_init_db_runs_migration_directory():
    init_db = Path("../scripts/init-db.sh").read_text(encoding="utf-8")

    assert "db/migrations/*.sql" in init_db
    assert "/docker-entrypoint-initdb.d/migrations/$(basename" in init_db
