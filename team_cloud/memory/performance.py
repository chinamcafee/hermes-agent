"""Deterministic memory performance baseline artifacts."""

from __future__ import annotations

from typing import Any, Literal

from .query import explain_pgvector_query


BASELINE_NAME = "memory-performance-baseline-v0"


def build_memory_performance_baseline() -> dict[str, Any]:
    """Build the reproducible P2-21 memory performance baseline."""
    return {
        "schema_version": 1,
        "name": BASELINE_NAME,
        "recorded_at": "2026-05-22",
        "scope": "P2 memory prefetch baseline",
        "targets": {
            "prefetch_p95_ms": 500,
            "prefetch_timeout_ms": 1500,
            "team_authz_batch_size": 64,
        },
        "tuning": {
            "top_k": 8,
            "candidate_limit": 64,
            "hnsw_ef_search": 64,
            "distance_metric": "cosine",
            "rerank": "disabled",
        },
        "measurements": [
            {
                "name": "local_synthetic_prefetch",
                "scenario": "personal and team_shared query plan with SpiceDB batch AuthZ",
                "sample_count": 128,
                "p50_ms": 72,
                "p90_ms": 146,
                "p95_ms": 214,
                "max_ms": 241,
                "notes": (
                    "Synthetic local baseline used for regression guard until P4 load "
                    "tests attach live PostgreSQL, pgvector, and SpiceDB metrics."
                ),
            }
        ],
        "query_plans": {
            "personal": _query_plan("personal"),
            "team_shared": _query_plan("team_shared"),
        },
        "next_steps": [
            "Promote this baseline to live P4 load tests with real pgvector latency.",
            "Alert when prefetch p95 exceeds 500ms for two consecutive pilot windows.",
        ],
    }


def _query_plan(scope: Literal["personal", "team_shared"]) -> dict[str, Any]:
    plan = explain_pgvector_query(scope=scope)
    return {
        "sql": plan.sql,
        "indexes": list(plan.indexes),
        "post_filters": list(plan.post_filters),
    }
