"""Performance tuning plan contract for Team Cloud Beta."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


_TUNING_ACTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "pgvector_hnsw",
        "area": "memory_prefetch",
        "settings": {
            "index": "idx_memory_embeddings_hnsw",
            "hnsw_ef_search": 96,
            "top_k": 8,
            "candidate_limit": 48,
            "distance_metric": "cosine",
        },
        "validation": [
            "memory_prefetch_p95_ms <= 500",
            "explain plan uses idx_memory_embeddings_hnsw",
        ],
    },
    {
        "id": "spicedb_batch_check",
        "area": "authz",
        "settings": {
            "api": "CheckBulkPermissions",
            "batch_size": 128,
            "cache_ttl_seconds": 30,
            "fail_closed": True,
        },
        "validation": [
            "spicedb_check_p95_ms <= 30",
            "deny_rate is explained by policy outcomes",
        ],
    },
    {
        "id": "worker_concurrency",
        "area": "workers",
        "settings": {
            "embedding_worker_concurrency": 12,
            "backup_worker_concurrency": 4,
            "outbox_worker_concurrency": 8,
            "max_retry_backoff_seconds": 60,
        },
        "validation": [
            "worker_lag_seconds <= 60",
            "dead_letter_count remains zero during pilot window",
        ],
    },
)


def build_performance_tuning_plan() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "name": "team-cloud-performance-tuning-v0",
        "source_baselines": [
            "teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json",
            "teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json",
        ],
        "targets": {
            "memory_prefetch_p95_ms": 500,
            "spicedb_check_p95_ms": 30,
            "worker_lag_seconds": 60,
            "chat_run_p95_ms": 2500,
        },
        "load_scenarios": [
            "memory_prefetch",
            "spicedb_batch_check",
            "embedding_import",
            "personal_backup",
            "gateway_group_session",
        ],
        "tuning_actions": deepcopy(list(_TUNING_ACTIONS)),
        "rollback": [
            "rollback_to_p2_baseline",
            "restore_previous_worker_concurrency",
            "disable_authz_cache_if_deny_drift_detected",
        ],
        "telemetry_required": [
            "team_cloud_pgvector_query_latency_ms",
            "team_cloud_spicedb_check_latency_ms",
            "team_cloud_worker_lag_seconds",
            "authz.cache_hit_rate",
        ],
    }


__all__ = ["build_performance_tuning_plan"]
