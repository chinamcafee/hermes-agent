from __future__ import annotations

from datetime import UTC, datetime


NOW = datetime(2026, 5, 22, 12, 0, tzinfo=UTC)


def test_restore_execute_merge_creates_new_memories_and_skips_duplicates():
    from team_cloud.backup.restore import RestoreExecutionService
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    existing = memory_service.create_memory(_memory_payload("Existing memory."))
    preview = _preview(
        [
            {
                "action": "skip",
                "reason": "checksum_match",
                "current_memory_id": existing["id"],
                "source": _source("backup-existing", "Existing memory."),
            },
            {
                "action": "create",
                "reason": "new_memory",
                "current_memory_id": None,
                "source": _source("backup-new", "Restored new memory."),
            },
        ]
    )
    service = RestoreExecutionService(memory_service=memory_service, now=lambda: NOW)

    job = service.execute_preview(
        preview,
        mode="merge",
        actor_member_id="alice",
    )

    restored = [
        memory
        for memory in memory_service.items.values()
        if memory["content"] == "Restored new memory."
    ]
    assert job["id"] == "restore-job-1"
    assert job["status"] == "succeeded"
    assert job["mode"] == "merge"
    assert job["summary"] == {
        "created": 1,
        "updated": 0,
        "archived": 0,
        "skipped": 1,
        "conflicts": 0,
    }
    assert len(restored) == 1
    assert restored[0]["scope"] == "personal"
    assert restored[0]["subject_member_id"] == "alice"
    assert service.embedding_rebuild_queue == [restored[0]["id"]]


def test_restore_execute_overwrite_updates_current_memory_and_requests_embedding():
    from team_cloud.backup.restore import RestoreExecutionService
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    current = memory_service.create_memory(_memory_payload("Old content."))
    preview = _preview(
        [
            {
                "action": "conflict",
                "reason": "backup_newer",
                "current_memory_id": current["id"],
                "source": _source("backup-current", "Restored overwrite content."),
            }
        ]
    )
    service = RestoreExecutionService(memory_service=memory_service, now=lambda: NOW)

    job = service.execute_preview(
        preview,
        mode="overwrite",
        actor_member_id="alice",
    )

    updated = memory_service.items[current["id"]]
    assert updated["content"] == "Restored overwrite content."
    assert updated["version"] == 2
    assert job["summary"]["updated"] == 1
    assert service.embedding_rebuild_queue == [current["id"]]


def test_restore_execute_archive_current_then_restore_archives_and_creates():
    from team_cloud.backup.restore import RestoreExecutionService
    from team_cloud.memory.service import InMemoryMemoryService

    memory_service = InMemoryMemoryService()
    current = memory_service.create_memory(_memory_payload("Conflicting current."))
    preview = _preview(
        [
            {
                "action": "conflict",
                "reason": "current_deleted",
                "current_memory_id": current["id"],
                "source": _source("backup-conflict", "Restored conflict content."),
            }
        ]
    )
    service = RestoreExecutionService(memory_service=memory_service, now=lambda: NOW)

    job = service.execute_preview(
        preview,
        mode="archive_current_then_restore",
        actor_member_id="alice",
    )

    created = [
        memory
        for memory in memory_service.items.values()
        if memory["content"] == "Restored conflict content."
    ]
    assert memory_service.items[current["id"]]["status"] == "archived"
    assert len(created) == 1
    assert job["summary"]["archived"] == 1
    assert job["summary"]["created"] == 1
    assert service.embedding_rebuild_queue == [created[0]["id"]]


def _preview(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "id": "restore-preview-1",
        "org_id": "org-1",
        "member_id": "alice",
        "backup_id": "backup-1",
        "status": "previewed",
        "items": items,
    }


def _source(memory_id: str, content: str) -> dict[str, object]:
    return {
        "id": memory_id,
        "org_id": "org-1",
        "scope": "personal",
        "subject_member_id": "alice",
        "content": content,
        "memory_type": "fact",
        "sensitivity": "normal",
        "source_type": "backup",
        "source_ref": {"backup_id": "backup-1"},
    }


def _memory_payload(content: str) -> dict[str, object]:
    return {
        "org_id": "org-1",
        "scope": "personal",
        "subject_member_id": "alice",
        "content": content,
    }
