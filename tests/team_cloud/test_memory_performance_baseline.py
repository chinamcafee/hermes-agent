from __future__ import annotations

import json
import os
from pathlib import Path


BASELINE_ARTIFACT = Path("teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json")
BASELINE_SCRIPT = Path("scripts/team-cloud-memory-perf-baseline.py")


def test_memory_performance_baseline_artifact_records_prefetch_p95_and_query_plan():
    data = json.loads(BASELINE_ARTIFACT.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["name"] == "memory-performance-baseline-v0"
    assert data["targets"]["prefetch_p95_ms"] == 500
    assert data["measurements"][0]["p95_ms"] <= data["targets"]["prefetch_p95_ms"]
    assert data["tuning"]["top_k"] == 8
    assert data["tuning"]["candidate_limit"] <= 64
    assert "idx_memory_embeddings_hnsw" in data["query_plans"]["personal"]["indexes"]
    assert "idx_memory_embeddings_hnsw" in data["query_plans"]["team_shared"]["indexes"]
    assert (
        "spicedb batch_check(memory#read_team)"
        in data["query_plans"]["team_shared"]["post_filters"]
    )


def test_memory_performance_baseline_builder_matches_artifact():
    from team_cloud.memory.performance import build_memory_performance_baseline

    built = build_memory_performance_baseline()
    artifact = json.loads(BASELINE_ARTIFACT.read_text(encoding="utf-8"))

    assert built["targets"] == artifact["targets"]
    assert built["tuning"] == artifact["tuning"]
    assert built["query_plans"] == artifact["query_plans"]


def test_memory_performance_baseline_script_is_reproducible():
    content = BASELINE_SCRIPT.read_text(encoding="utf-8")

    assert os.access(BASELINE_SCRIPT, os.X_OK)
    assert "memory-performance-baseline-v0.json" in content
    assert "build_memory_performance_baseline" in content
