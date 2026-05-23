from __future__ import annotations

from pathlib import Path


MEMORY_MIGRATION = Path("team_cloud/sql_migrations/002_memory_runtime_schema.sql")
ROLLBACK_NOTE = Path("team_cloud/sql_migrations/002_memory_runtime_schema.rollback.md")


def test_memory_runtime_migration_adds_p2_memory_columns_and_indexes():
    sql = MEMORY_MIGRATION.read_text(encoding="utf-8").lower()

    assert "alter table memory_items" in sql
    assert "add column if not exists memory_type" in sql
    assert "add column if not exists source_event_id" in sql
    assert "alter table memory_observations" in sql
    assert "add column if not exists extraction_trace" in sql
    assert "add column if not exists confidence" in sql
    assert "alter table memory_review_items" in sql
    assert "add column if not exists review_kind" in sql
    assert "add column if not exists candidate_payload" in sql
    assert "idx_memory_items_scope_type_status" in sql
    assert "idx_memory_review_pending_kind" in sql
    assert "idx_memory_observations_pending" in sql


def test_memory_runtime_migration_has_rollback_note():
    note = ROLLBACK_NOTE.read_text(encoding="utf-8").lower()

    assert "002_memory_runtime_schema.sql" in note
    assert "rollback" in note
    assert "drop column" in note
    assert "drop index" in note
