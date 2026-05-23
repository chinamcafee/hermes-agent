from __future__ import annotations


def test_personal_memory_query_filters_to_current_member_and_records_read_ids():
    from team_cloud.memory.query import InMemoryMemoryQueryRepository, MemoryItem, MemoryQueryService

    repository = InMemoryMemoryQueryRepository(
        [
            MemoryItem(
                id="mem-alice",
                org_id="org-1",
                scope="personal",
                subject_member_id="alice",
                team_id=None,
                project_id=None,
                status="active",
                sensitivity="normal",
                memory_type="fact",
                content="Alice likes deterministic tests.",
                embedding=(1.0, 0.0, 0.0),
            ),
            MemoryItem(
                id="mem-bob",
                org_id="org-1",
                scope="personal",
                subject_member_id="bob",
                team_id=None,
                project_id=None,
                status="active",
                sensitivity="normal",
                memory_type="fact",
                content="Bob private memory.",
                embedding=(1.0, 0.0, 0.0),
            ),
        ]
    )
    service = MemoryQueryService(repository=repository)

    results = service.query_personal(
        org_id="org-1",
        member_id="alice",
        query_embedding=(1.0, 0.0, 0.0),
        limit=5,
    )

    assert [item.id for item in results.items] == ["mem-alice"]
    assert results.read_memory_ids == ("mem-alice",)


def test_team_memory_query_filters_context_and_applies_spicedb_batch_check():
    from team_cloud.authz.spicedb import PermissionDecision
    from team_cloud.memory.query import InMemoryMemoryQueryRepository, MemoryItem, MemoryQueryService

    class FakeAuthzClient:
        def __init__(self):
            self.checks = []

        def batch_check(self, checks):
            self.checks = list(checks)
            return tuple(
                PermissionDecision(
                    allowed=check.resource.id == "mem-team-allowed",
                    reason="allowed" if check.resource.id == "mem-team-allowed" else "denied",
                    subject=check.subject,
                    resource=check.resource,
                    permission="read_team",
                )
                for check in self.checks
            )

    authz_client = FakeAuthzClient()
    repository = InMemoryMemoryQueryRepository(
        [
            MemoryItem(
                id="mem-team-allowed",
                org_id="org-1",
                scope="team_shared",
                subject_member_id=None,
                team_id="team-1",
                project_id="project-1",
                status="active",
                sensitivity="normal",
                memory_type="procedure",
                content="Team runbook.",
                embedding=(1.0, 0.0, 0.0),
            ),
            MemoryItem(
                id="mem-team-denied",
                org_id="org-1",
                scope="team_shared",
                subject_member_id=None,
                team_id="team-1",
                project_id="project-1",
                status="active",
                sensitivity="normal",
                memory_type="fact",
                content="Denied team memory.",
                embedding=(0.9, 0.1, 0.0),
            ),
            MemoryItem(
                id="mem-other-team",
                org_id="org-1",
                scope="team_shared",
                subject_member_id=None,
                team_id="team-2",
                project_id="project-1",
                status="active",
                sensitivity="normal",
                memory_type="fact",
                content="Other team memory.",
                embedding=(1.0, 0.0, 0.0),
            ),
        ]
    )
    service = MemoryQueryService(repository=repository, authz_client=authz_client)

    results = service.query_team(
        org_id="org-1",
        team_id="team-1",
        project_id="project-1",
        subject_type="user",
        subject_id="alice",
        query_embedding=(1.0, 0.0, 0.0),
        limit=5,
    )

    assert [item.id for item in results.items] == ["mem-team-allowed"]
    assert results.read_memory_ids == ("mem-team-allowed",)
    assert [check.resource.as_spicedb() for check in authz_client.checks] == [
        "memory:mem-team-allowed",
        "memory:mem-team-denied",
    ]


def test_memory_query_explain_contains_pgvector_filters_and_hnsw_index():
    from team_cloud.memory.query import explain_pgvector_query

    personal = explain_pgvector_query(scope="personal")
    team = explain_pgvector_query(scope="team_shared")

    assert "memory_embeddings.embedding <=> :query_embedding" in personal.sql
    assert "memory_items.subject_member_id = :member_id" in personal.sql
    assert "idx_memory_embeddings_hnsw" in personal.indexes
    assert "memory_items.team_id = :team_id" in team.sql
    assert "memory_items.project_id = :project_id" in team.sql
    assert "spicedb batch_check(memory#read_team)" in team.post_filters
