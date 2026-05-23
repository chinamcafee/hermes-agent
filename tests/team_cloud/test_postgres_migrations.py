from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

PACKAGE_MIGRATION = Path("team_cloud/sql_migrations/001_schema_v0.sql")
MEMORY_MIGRATION = Path("team_cloud/sql_migrations/002_memory_runtime_schema.sql")
P0_ARTIFACT = Path("teamDoc/GADoc/artifacts/postgres/001_schema_v0.sql")
ROLLBACK_NOTE = Path("team_cloud/sql_migrations/001_schema_v0.rollback.md")
GADOC_PATH = Path("teamDoc/GADoc/P1-04-postgres-base-migrations.md")
COMPOSE_PATH = Path("deploy/team-cloud/compose.yaml")

CORE_TABLES = {
    "team_cloud_users",
    "organizations",
    "members",
    "teams",
    "projects",
    "external_identities",
    "service_accounts",
    "api_tokens",
    "spicedb_outbox",
    "audit_events",
}


def test_packaged_migration_promotes_p0_artifact_verbatim():
    assert PACKAGE_MIGRATION.exists()
    assert PACKAGE_MIGRATION.read_text(encoding="utf-8") == P0_ARTIFACT.read_text(
        encoding="utf-8"
    )


def test_base_migration_contains_extensions_and_core_tables():
    sql = PACKAGE_MIGRATION.read_text(encoding="utf-8").lower()

    assert "create extension if not exists pgcrypto" in sql
    assert "create extension if not exists vector" in sql
    for table_name in CORE_TABLES:
        assert f"create table if not exists {table_name}" in sql


def test_base_migration_has_rollback_note():
    note = ROLLBACK_NOTE.read_text(encoding="utf-8")

    assert "001_schema_v0.sql" in note
    assert "rollback" in note.lower()
    assert "drop" in note.lower()


def test_migration_runner_uses_packaged_sql_and_checksums():
    from team_cloud.migrations import MigrationRunner

    expected_paths = [PACKAGE_MIGRATION, MEMORY_MIGRATION]
    expected_checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in expected_paths
    }

    plan = MigrationRunner.default().plan()
    assert [migration.name for migration in plan] == [
        "001_schema_v0.sql",
        "002_memory_runtime_schema.sql",
    ]
    assert {migration.name: migration.checksum_sha256 for migration in plan} == expected_checksums

    dry_run = MigrationRunner.default().dry_run()
    assert dry_run["migrations"] == [
        "001_schema_v0.sql",
        "002_memory_runtime_schema.sql",
    ]
    assert dry_run["checksums"] == expected_checksums


def test_migration_runner_builds_psql_apply_commands():
    from team_cloud.migrations import MigrationRunner

    commands = MigrationRunner.default().psql_apply_commands(
        "postgresql://hermes_team_user:secret@postgres:5432/hermes_team?sslmode=disable"
    )

    assert len(commands) == 2
    for command in commands:
        assert command[:3] == ["psql", "--set", "ON_ERROR_STOP=1"]
        assert "-f" in command
    assert str(PACKAGE_MIGRATION.resolve()) in commands[0]
    assert str(MEMORY_MIGRATION.resolve()) in commands[1]


def test_compose_has_team_migrate_job_before_team_api():
    compose = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    services = compose["services"]

    assert "team-migrate" in services
    assert "team_cloud_database_url" in services["team-migrate"]["secrets"]
    assert "../../team_cloud/sql_migrations:/migrations:ro" in str(services["team-migrate"])
    assert "for migration in /migrations/*.sql" in str(services["team-migrate"])
    assert services["team-api"]["depends_on"]["team-migrate"][
        "condition"
    ] == "service_completed_successfully"


def test_gadoc_references_migration_artifacts():
    doc = GADOC_PATH.read_text(encoding="utf-8")

    assert "team_cloud/sql_migrations/001_schema_v0.sql" in doc
    assert "team_cloud/sql_migrations/001_schema_v0.rollback.md" in doc
    assert "team-migrate" in doc
