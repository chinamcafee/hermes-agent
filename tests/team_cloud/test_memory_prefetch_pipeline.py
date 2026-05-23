from __future__ import annotations

from fastapi.testclient import TestClient


def _pipeline():
    from team_cloud.authz.spicedb import PermissionDecision
    from team_cloud.memory.prefetch import StaticEmbeddingProvider, MemoryPrefetchPipeline
    from team_cloud.memory.query import InMemoryMemoryQueryRepository, MemoryItem, MemoryQueryService

    class AllowingAuthzClient:
        def batch_check(self, checks):
            return tuple(
                PermissionDecision(
                    allowed=True,
                    reason="allowed",
                    subject=check.subject,
                    resource=check.resource,
                    permission="read_team",
                )
                for check in checks
            )

    repository = InMemoryMemoryQueryRepository(
        [
            MemoryItem(
                id="personal-1",
                org_id="org-1",
                scope="personal",
                subject_member_id="alice",
                team_id=None,
                project_id=None,
                status="active",
                sensitivity="normal",
                memory_type="preference",
                content="Alice prefers deterministic tests.",
                embedding=(1.0, 0.0, 0.0),
            ),
            MemoryItem(
                id="team-1",
                org_id="org-1",
                scope="team_shared",
                subject_member_id=None,
                team_id="team-1",
                project_id="project-1",
                status="active",
                sensitivity="normal",
                memory_type="procedure",
                content="Team runbook for releases.",
                embedding=(1.0, 0.0, 0.0),
            ),
        ]
    )
    query_service = MemoryQueryService(
        repository=repository,
        authz_client=AllowingAuthzClient(),
    )
    return MemoryPrefetchPipeline(
        embedding_provider=StaticEmbeddingProvider((1.0, 0.0, 0.0)),
        query_service=query_service,
    )


def test_prefetch_pipeline_returns_personal_and_team_partitions_with_memory_ids():
    result = _pipeline().prefetch(
        query="release process",
        org_id="org-1",
        member_id="alice",
        team_id="team-1",
        project_id="project-1",
        limit=5,
    )

    assert [partition["scope"] for partition in result["partitions"]] == [
        "personal",
        "team_shared",
    ]
    assert result["memory_ids"] == ["personal-1", "team-1"]
    assert result["partitions"][0]["items"][0]["id"] == "personal-1"
    assert result["partitions"][1]["items"][0]["id"] == "team-1"


def test_prefetch_api_exposes_pipeline_response():
    from team_cloud.api import create_app

    client = TestClient(
        create_app(memory_prefetch_pipeline=_pipeline(), oidc_client=object())
    )

    response = client.post(
        "/v1/memory/prefetch",
        json={
            "query": "release process",
            "org_id": "org-1",
            "member_id": "alice",
            "team_id": "team-1",
            "project_id": "project-1",
            "limit": 5,
        },
    )

    assert response.status_code == 200
    assert response.json()["memory_ids"] == ["personal-1", "team-1"]


def test_prefetch_pipeline_can_disable_personal_partition_for_shared_sessions():
    result = _pipeline().prefetch(
        query="release process",
        org_id="org-1",
        member_id="alice",
        team_id="team-1",
        project_id="project-1",
        limit=5,
        include_personal=False,
    )

    assert result["memory_ids"] == ["team-1"]
    personal_partition = result["partitions"][0]
    assert personal_partition["scope"] == "personal"
    assert personal_partition["items"] == []
