"""Migration discovery and psql command primitives for Team Cloud."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Migration:
    name: str
    path: Path
    checksum_sha256: str


class MigrationRunner:
    def __init__(self, migrations_dir: str | Path):
        self.migrations_dir = Path(migrations_dir)

    @classmethod
    def default(cls) -> "MigrationRunner":
        return cls(Path(__file__).resolve().parent / "sql_migrations")

    def plan(self) -> list[Migration]:
        if not self.migrations_dir.exists():
            return []
        return [
            Migration(
                name=path.name,
                path=path,
                checksum_sha256=_sha256(path),
            )
            for path in sorted(self.migrations_dir.glob("*.sql"))
        ]

    def dry_run(self) -> dict[str, object]:
        migrations = self.plan()
        return {
            "status": "ok",
            "count": len(migrations),
            "migrations": [migration.name for migration in migrations],
            "checksums": {
                migration.name: migration.checksum_sha256 for migration in migrations
            },
        }

    def psql_apply_commands(self, database_url: str) -> list[list[str]]:
        return [
            [
                "psql",
                "--set",
                "ON_ERROR_STOP=1",
                database_url,
                "-f",
                str(migration.path.resolve()),
            ]
            for migration in self.plan()
        ]

    def apply_psql(self, database_url: str) -> list[subprocess.CompletedProcess[str]]:
        results: list[subprocess.CompletedProcess[str]] = []
        for command in self.psql_apply_commands(database_url):
            results.append(
                subprocess.run(
                    command,
                    check=True,
                    text=True,
                    capture_output=True,
                )
            )
        return results


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
