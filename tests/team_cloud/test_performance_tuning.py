from __future__ import annotations

import json
import os
from pathlib import Path


ARTIFACT = Path("teamDoc/GADoc/artifacts/load/team-cloud-performance-tuning-v0.json")
DOC = Path("teamDoc/GADoc/P4-16-performance-tuning.md")
SCRIPT = Path("scripts/team-cloud-performance-tuning.py")
SMOKE_SCRIPT = Path("scripts/team-cloud-foundation-smoke.sh")
SMOKE_MATRIX = Path("teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json")


def test_performance_tuning_plan_covers_pgvector_batch_authz_and_workers():
    from team_cloud.performance_tuning import build_performance_tuning_plan

    plan = build_performance_tuning_plan()
    tuning = {item["id"]: item for item in plan["tuning_actions"]}

    assert plan["schema_version"] == 1
    assert plan["name"] == "team-cloud-performance-tuning-v0"
    assert plan["targets"]["memory_prefetch_p95_ms"] <= 500
    assert plan["targets"]["spicedb_check_p95_ms"] <= 30
    assert plan["targets"]["worker_lag_seconds"] <= 60
    assert {"pgvector_hnsw", "spicedb_batch_check", "worker_concurrency"} <= set(tuning)
    assert tuning["pgvector_hnsw"]["settings"]["index"] == "idx_memory_embeddings_hnsw"
    assert tuning["pgvector_hnsw"]["settings"]["candidate_limit"] <= 64
    assert tuning["spicedb_batch_check"]["settings"]["batch_size"] >= 64
    assert tuning["worker_concurrency"]["settings"]["embedding_worker_concurrency"] >= 8
    assert "memory_prefetch" in plan["load_scenarios"]
    assert "spicedb_batch_check" in plan["load_scenarios"]
    assert "embedding_import" in plan["load_scenarios"]
    assert "rollback_to_p2_baseline" in plan["rollback"]


def test_performance_tuning_artifact_script_docs_and_smoke_are_registered():
    from team_cloud.performance_tuning import build_performance_tuning_plan

    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    script = SCRIPT.read_text(encoding="utf-8")
    smoke = SMOKE_SCRIPT.read_text(encoding="utf-8")
    matrix = json.loads(SMOKE_MATRIX.read_text(encoding="utf-8"))
    domains = {entry["domain"] for entry in matrix["checks"]}

    assert artifact == build_performance_tuning_plan()
    assert os.access(SCRIPT, os.X_OK)
    assert "team-cloud-performance-tuning-v0.json" in script
    assert "pgvector_hnsw" in doc
    assert "spicedb_batch_check" in doc
    assert "worker_concurrency" in doc
    assert "tests/team_cloud/test_performance_tuning.py" in smoke
    assert "performance_tuning" in domains
