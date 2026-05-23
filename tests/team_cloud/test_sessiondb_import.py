from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


IMPORT_SCRIPT = Path("scripts/team-cloud-import-sessiondb.py")


def _build_local_sessiondb(tmp_path: Path) -> Path:
    from hermes_state import SessionDB

    db_path = tmp_path / "state.db"
    db = SessionDB(db_path=db_path)
    db.create_session(
        "local-session-1",
        source="cli",
        user_id="alice-local",
        model="gpt-test",
    )
    db.append_message("local-session-1", "user", "Summarize the roadmap.")
    db.append_message(
        "local-session-1",
        "assistant",
        "Roadmap summarized.",
        tool_calls=[
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "team_memory_search", "arguments": "{}"},
            }
        ],
    )
    db.create_session(
        "local-session-2",
        source="telegram",
        user_id="bob-unmapped",
        model="gpt-test",
    )
    db.append_message("local-session-2", "user", "This should not import.")
    db.close()
    return db_path


def test_sessiondb_import_maps_local_history_into_cloud_sessions(tmp_path):
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.sessiondb_import import import_sessiondb

    db_path = _build_local_sessiondb(tmp_path)
    repository = InMemoryCloudSessionRepository()

    report = import_sessiondb(
        db_path,
        repository,
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        identity_map={"alice-local": "alice"},
    )

    assert report["schema_version"] == 1
    assert report["imported_session_count"] == 1
    assert report["imported_message_count"] == 2
    assert report["unmapped_session_count"] == 1
    imported = report["imported_sessions"][0]
    history = repository.get_session(imported["cloud_session_id"])

    assert imported["local_session_id"] == "local-session-1"
    assert imported["member_id"] == "alice"
    assert history["org_id"] == "org-1"
    assert history["team_id"] == "team-1"
    assert history["project_id"] == "project-1"
    assert history["owner_member_id"] == "alice"
    assert history["source_platform"] == "sessiondb:cli"
    assert history["messages"][0]["role"] == "user"
    assert history["messages"][0]["content"]["text"] == "Summarize the roadmap."
    assert history["messages"][1]["role"] == "assistant"
    assert history["messages"][1]["content"]["tool_calls"][0]["id"] == "call-1"


def test_sessiondb_import_reports_unmapped_identities_without_creating_sessions(tmp_path):
    from team_cloud.cloud_sessions import InMemoryCloudSessionRepository
    from team_cloud.sessiondb_import import import_sessiondb

    db_path = _build_local_sessiondb(tmp_path)
    repository = InMemoryCloudSessionRepository()

    report = import_sessiondb(
        db_path,
        repository,
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        identity_map={},
    )

    assert report["imported_session_count"] == 0
    assert report["imported_message_count"] == 0
    assert report["unmapped_session_count"] == 2
    assert report["unmapped_sessions"] == [
        {
            "local_session_id": "local-session-1",
            "source": "cli",
            "user_id": "alice-local",
            "reason": "identity_not_mapped",
        },
        {
            "local_session_id": "local-session-2",
            "source": "telegram",
            "user_id": "bob-unmapped",
            "reason": "identity_not_mapped",
        },
    ]
    assert repository.list_sessions(org_id="org-1") == []


def test_sessiondb_import_script_supports_dry_run_report(tmp_path):
    db_path = _build_local_sessiondb(tmp_path)
    identity_map = tmp_path / "identity-map.json"
    identity_map.write_text(json.dumps({"alice-local": "alice"}), encoding="utf-8")

    result = subprocess.run(
        [
            "venv/bin/python",
            str(IMPORT_SCRIPT),
            "--db",
            str(db_path),
            "--org-id",
            "org-1",
            "--team-id",
            "team-1",
            "--project-id",
            "project-1",
            "--identity-map",
            str(identity_map),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    content = IMPORT_SCRIPT.read_text(encoding="utf-8")

    assert os.access(IMPORT_SCRIPT, os.X_OK)
    assert "import_sessiondb" in content
    assert "--identity-map" in content
    assert report["dry_run"] is True
    assert report["imported_session_count"] == 1
    assert report["imported_sessions"][0]["cloud_session_id"] is None
    assert report["unmapped_session_count"] == 1
