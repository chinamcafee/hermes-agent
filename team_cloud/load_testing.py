"""Load-test plan contract for Team Cloud Beta validation."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "id": "concurrent_chat_runs",
        "domain": "chat",
        "description": "Concurrent Web Chat runs through Team Cloud.",
        "entrypoint": "POST /api/chat/runs",
        "concurrency": 50,
        "duration_seconds": 600,
        "target_p95_ms": 2500,
        "success_criteria": {"error_rate": 0.01, "min_successful_runs": 1000},
        "telemetry": [
            "team_cloud_http_requests_total",
            "team_cloud_worker_lag_seconds",
            "chat_run.status",
        ],
    },
    {
        "id": "memory_prefetch",
        "domain": "memory",
        "description": "Concurrent personal and team memory prefetch calls.",
        "entrypoint": "POST /v1/memory/prefetch",
        "concurrency": 40,
        "duration_seconds": 600,
        "target_p95_ms": 500,
        "success_criteria": {"error_rate": 0.005, "min_successful_runs": 2000},
        "telemetry": [
            "team_cloud_pgvector_query_latency_ms",
            "spicedb batch_check(memory#read_team)",
            "prefetch.result_count",
        ],
    },
    {
        "id": "spicedb_batch_check",
        "domain": "authz",
        "description": "Batched permission checks for team memory and tools.",
        "entrypoint": "SpiceDB CheckBulkPermissions",
        "concurrency": 64,
        "duration_seconds": 600,
        "target_p95_ms": 250,
        "success_criteria": {"error_rate": 0.001, "min_successful_runs": 5000},
        "telemetry": [
            "team_cloud_spicedb_check_latency_ms",
            "team_cloud_spicedb_denies_total",
            "authz.cache_hit_rate",
        ],
    },
    {
        "id": "embedding_import",
        "domain": "memory",
        "description": "Bulk memory embedding backfill and import.",
        "entrypoint": "memory embedding worker",
        "concurrency": 8,
        "duration_seconds": 900,
        "target_p95_ms": 1200,
        "success_criteria": {"error_rate": 0.005, "min_successful_runs": 10000},
        "telemetry": [
            "team_cloud_worker_lag_seconds",
            "embedding.batch_size",
            "embedding.retry_count",
        ],
    },
    {
        "id": "personal_backup",
        "domain": "backup",
        "description": "Scheduled encrypted personal memory backups.",
        "entrypoint": "personal backup worker",
        "concurrency": 20,
        "duration_seconds": 900,
        "target_p95_ms": 5000,
        "success_criteria": {"error_rate": 0, "min_successful_runs": 200},
        "telemetry": [
            "team_cloud_minio_operation_latency_ms",
            "backup_job.status",
            "backup_manifest.checksum",
        ],
    },
    {
        "id": "org_export",
        "domain": "governance",
        "description": "Organization export with sessions, memory, and relationships.",
        "entrypoint": "org export service",
        "concurrency": 5,
        "duration_seconds": 600,
        "target_p95_ms": 15000,
        "success_criteria": {"error_rate": 0, "min_successful_runs": 25},
        "telemetry": [
            "export_job.status",
            "team_cloud_minio_operation_latency_ms",
            "relationship_snapshot.count",
        ],
    },
    {
        "id": "gateway_group_session",
        "domain": "gateway",
        "description": "Gateway group session identity resolution and chat submit.",
        "entrypoint": "gateway -> Team Cloud identity resolver",
        "concurrency": 30,
        "duration_seconds": 600,
        "target_p95_ms": 3000,
        "success_criteria": {"error_rate": 0.01, "min_successful_runs": 600},
        "telemetry": [
            "gateway.identity_resolution_ms",
            "team_cloud_http_requests_total",
            "chat_run.status",
        ],
    },
)


def build_load_test_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-load-test-plan-v0",
        "runner": {
            "script": "scripts/team-cloud-load-test-plan.py",
            "artifact": "teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json",
            "mode": "plan_contract",
        },
        "global_success_criteria": {
            "p0_p1_incidents": 0,
            "security_denies_expected_only": True,
            "telemetry_required": True,
        },
        "scenarios": deepcopy(list(_SCENARIOS)),
    }


__all__ = ["build_load_test_plan"]
