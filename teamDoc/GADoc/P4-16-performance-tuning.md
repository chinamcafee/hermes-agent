# P4-16 性能调优

日期：2026-05-23
状态：Implemented
前置：`P4-07 Load test scripts`

## 目标

本步骤固定 P4 性能调优 contract，将 P2 memory baseline 和 P4 load scenarios 收敛到可执行的调优矩阵。

核心动作覆盖 `pgvector_hnsw`、`spicedb_batch_check` 和 `worker_concurrency`，目标是 memory prefetch P95 <= 500ms、SpiceDB check P95 <= 30ms、worker lag <= 60s。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/performance_tuning.py` | `build_performance_tuning_plan()` 生成性能调优矩阵。 |
| `scripts/team-cloud-performance-tuning.py` | 写出 performance tuning JSON artifact。 |
| `teamDoc/GADoc/artifacts/load/team-cloud-performance-tuning-v0.json` | P4-16 performance tuning artifact。 |
| `tests/team_cloud/test_performance_tuning.py` | P4-16 contract 测试。 |

## 调优动作

| id | 内容 |
| --- | --- |
| `pgvector_hnsw` | 固定 `idx_memory_embeddings_hnsw`、`hnsw_ef_search=96`、`top_k=8`、`candidate_limit=48`。 |
| `spicedb_batch_check` | 使用 `CheckBulkPermissions`、`batch_size=128`、短 TTL 缓存和 fail-closed 行为。 |
| `worker_concurrency` | embedding、backup、outbox worker 并发和 retry backoff 收敛到 pilot 可观测阈值。 |

## 运行

```bash
scripts/team-cloud-performance-tuning.py --output teamDoc/GADoc/artifacts/load/team-cloud-performance-tuning-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_performance_tuning.py
scripts/run_tests.sh tests/team_cloud/test_performance_tuning.py tests/team_cloud/test_load_test_scripts.py tests/team_cloud/test_memory_performance_baseline.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/performance_tuning.py scripts/team-cloud-performance-tuning.py tests/team_cloud/test_performance_tuning.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/performance_tuning.py scripts/team-cloud-performance-tuning.py tests/team_cloud/test_performance_tuning.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/load/team-cloud-performance-tuning-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
