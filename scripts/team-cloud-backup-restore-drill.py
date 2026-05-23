#!/usr/bin/env python
"""Run the local Team Cloud platform backup/restore drill."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from team_cloud.backup.drill import PlatformBackupRestoreDrill
from team_cloud.backup.exporter import BackupEncryptionKey
from team_cloud.memory.service import InMemoryMemoryService


ORG_KEY = b"3" * 32


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json",
        help="Path to write the drill evidence JSON.",
    )
    args = parser.parse_args()

    report = build_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(output)}, sort_keys=True))
    return 0


def build_report() -> dict:
    now = datetime(2026, 5, 23, 9, 30, tzinfo=UTC)
    source_memory = InMemoryMemoryService()
    target_memory = InMemoryMemoryService()
    source_memory.create_memory(
        {
            "org_id": "org-1",
            "scope": "personal",
            "subject_member_id": "alice",
            "content": "Alice wants backup drill evidence in the beta report.",
        }
    )
    drill = PlatformBackupRestoreDrill(
        key_resolver=_key_resolver,
        now=lambda: now,
        drill_id_factory=lambda: "platform-drill-1",
        backup_id_factory=lambda: "backup-platform-drill-1",
        preview_id_factory=lambda: "restore-preview-platform-drill-1",
    )
    return drill.run_platform_restore_drill(
        source_memory_service=source_memory,
        target_memory_service=target_memory,
        org_id="org-1",
        member_id="alice",
        actor_member_id="alice",
        snapshot_ids={
            "postgresql": "pg-snapshot-20260523",
            "spicedb": "spicedb-snapshot-20260523",
            "minio": "minio-snapshot-20260523",
            "casdoor": "casdoor-export-20260523",
            "org_export": "org-export-20260523",
        },
        outbox_replay_count=7,
        minio_object_count=4,
    )


def _key_resolver(org_id: str) -> BackupEncryptionKey:
    return BackupEncryptionKey(key_id=f"{org_id}-key", key=ORG_KEY)


if __name__ == "__main__":
    raise SystemExit(main())
