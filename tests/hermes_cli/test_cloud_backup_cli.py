from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


class FakeObjectStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}

    def put_object(self, key: str, body: bytes, content_type: str = "application/json") -> None:
        self.objects[key] = body
        self.content_types[key] = content_type

    def get_object(self, key: str) -> bytes:
        return self.objects[key]

    def list_objects(self, prefix: str) -> list[dict[str, object]]:
        return [
            {"key": key, "size": len(body), "last_modified": "2026-05-24T10:00:00Z"}
            for key, body in sorted(self.objects.items())
            if key.startswith(prefix)
        ]


def test_default_config_contains_cloud_backup_section(tmp_path):
    from hermes_cli.config import DEFAULT_CONFIG, load_config

    with patch.dict("os.environ", {"HERMES_HOME": str(tmp_path)}):
        config = load_config()

    assert DEFAULT_CONFIG["cloud_backup"]["enabled"] is False
    assert "memory_backup" not in DEFAULT_CONFIG
    assert config["cloud_backup"]["endpoint"] == ""
    assert config["cloud_backup"]["bucket"] == "hermes-personal-cloud-backups"
    assert config["cloud_backup"]["access_key_env"] == "HERMES_CLOUD_BACKUP_MINIO_ACCESS_KEY"
    assert config["cloud_backup"]["secret_key_env"] == "HERMES_CLOUD_BACKUP_MINIO_SECRET_KEY"


def test_cloud_backup_uploads_and_restores_profile_scoped_memory_files(tmp_path):
    from hermes_cli.config import load_config, load_env
    from hermes_cli.cloud_backup import (
        configure_cloud_backup,
        restore_cloud_backup,
        run_cloud_backup_now,
    )

    hermes_home = tmp_path / ".hermes"
    memories = hermes_home / "memories"
    memories.mkdir(parents=True)
    (memories / "MEMORY.md").write_text("team-independent personal memory\n", encoding="utf-8")
    (memories / "USER.md").write_text("user preference\n", encoding="utf-8")
    fake = FakeObjectStore()
    fixed_now = datetime(2026, 5, 24, 10, 30, 0, tzinfo=timezone.utc)

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        configure_cloud_backup(
            endpoint="http://minio.local:9000",
            bucket="hermes-backups",
            access_key="minio",
            secret_key="miniopass",
            region="us-east-1",
            root_prefix="personal",
            print_fn=lambda _: None,
        )
        result = run_cloud_backup_now("memory", client=fake, now=fixed_now, print_fn=lambda _: None)
        config = load_config()
        env = load_env()

        assert config["cloud_backup"]["enabled"] is True
        assert env["HERMES_CLOUD_BACKUP_MINIO_ACCESS_KEY"] == "minio"
        assert env["HERMES_CLOUD_BACKUP_MINIO_SECRET_KEY"] == "miniopass"
        assert result["object_key"] == "personal/profiles/.hermes/memory/20260524T103000Z-personal-memory.json"
        payload = json.loads(fake.objects[result["object_key"]].decode("utf-8"))
        assert payload["format"] == "hermes-cloud-backup-memory-v1"
        assert payload["resource_type"] == "memory"
        assert payload["files"][0]["path"] == "memories/MEMORY.md"
        assert base64.b64decode(payload["files"][0]["content_base64"]).decode("utf-8") == "team-independent personal memory\n"

        (memories / "MEMORY.md").write_text("changed\n", encoding="utf-8")
        (memories / "USER.md").unlink()
        restore = restore_cloud_backup("memory", result["object_key"], client=fake, print_fn=lambda _: None)

    assert restore["restored_count"] == 2
    assert (memories / "MEMORY.md").read_text(encoding="utf-8") == "team-independent personal memory\n"
    assert (memories / "USER.md").read_text(encoding="utf-8") == "user preference\n"


def test_cloud_backup_uploads_and_restores_local_soul_file(tmp_path):
    from hermes_cli.cloud_backup import restore_cloud_backup, run_cloud_backup_now

    hermes_home = tmp_path / ".hermes"
    hermes_home.mkdir(parents=True)
    (hermes_home / "SOUL.md").write_text("local soul v1\n", encoding="utf-8")
    fake = FakeObjectStore()
    fixed_now = datetime(2026, 5, 24, 11, 0, 0, tzinfo=timezone.utc)

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        result = run_cloud_backup_now(
            "soul",
            client=fake,
            config={"cloud_backup": {"prefix": "personal"}},
            now=fixed_now,
            print_fn=lambda _: None,
        )
        assert result["object_key"] == "personal/profiles/.hermes/soul/20260524T110000Z-local-soul.json"
        payload = json.loads(fake.objects[result["object_key"]].decode("utf-8"))
        assert payload["format"] == "hermes-cloud-backup-soul-v1"
        assert payload["resource_type"] == "soul"
        assert payload["files"][0]["path"] == "SOUL.md"

        (hermes_home / "SOUL.md").write_text("changed\n", encoding="utf-8")
        restore = restore_cloud_backup("soul", result["object_key"], client=fake, print_fn=lambda _: None)

    assert restore["restored_count"] == 1
    assert (hermes_home / "SOUL.md").read_text(encoding="utf-8") == "local soul v1\n"


def test_cloud_backup_rejects_cross_resource_restore(tmp_path):
    from hermes_cli.cloud_backup import CloudBackupError, restore_cloud_backup, run_cloud_backup_now

    hermes_home = tmp_path / ".hermes"
    (hermes_home / "memories").mkdir(parents=True)
    (hermes_home / "memories" / "MEMORY.md").write_text("personal memory\n", encoding="utf-8")
    fake = FakeObjectStore()

    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        result = run_cloud_backup_now(
            "memory",
            client=fake,
            config={"cloud_backup": {"prefix": "personal"}},
            now=datetime(2026, 5, 24, 12, 0, 0, tzinfo=timezone.utc),
            print_fn=lambda _: None,
        )
        try:
            restore_cloud_backup("soul", result["object_key"], client=fake, print_fn=lambda _: None)
        except CloudBackupError as exc:
            assert str(exc) == "cloud_backup_resource_mismatch"
        else:
            raise AssertionError("expected resource mismatch")


def test_cloud_backup_schedule_creates_no_agent_cron_job(tmp_path):
    from hermes_cli.cloud_backup import schedule_cloud_backup

    hermes_home = tmp_path / ".hermes"
    with patch.dict("os.environ", {"HERMES_HOME": str(hermes_home)}, clear=False):
        from cron.jobs import list_jobs

        job = schedule_cloud_backup("memory", "daily", print_fn=lambda _: None)
        jobs = list_jobs(include_disabled=True)

    assert job["name"] == "Hermes cloud backup: memory"
    assert job["no_agent"] is True
    assert job["script"] == "cloud-backup-memory-cron.py"
    assert any(item["id"] == job["id"] for item in jobs)
    assert (hermes_home / "scripts" / "cloud-backup-memory-cron.py").exists()


def test_cloud_backup_slash_command_replaces_memory_backup():
    from hermes_cli.commands import resolve_command

    assert resolve_command("memory-backup") is None
    assert resolve_command("memory_backup") is None
    command = resolve_command("cloud-backup")
    assert command is not None
    assert command.name == "cloud-backup"
    assert command.cli_only is True
