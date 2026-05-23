# P2-21 记忆性能基线

日期：2026-05-22
状态：Implemented
前置：`P2-04 Prefetch pipeline`、`P2-20 隔离测试套件`

## 目标

本步骤建立双层记忆召回的可重复性能基线，覆盖 prefetch P95 目标、top-k/candidate limit、pgvector explain plan 和 team_shared AuthZ 后置过滤。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/performance.py` | 生成 canonical memory performance baseline。 |
| `scripts/team-cloud-memory-perf-baseline.py` | 将 baseline 写入 GADoc artifact 的可重复脚本。 |
| `teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json` | P2-21 性能基线 artifact。 |
| `tests/team_cloud/test_memory_performance_baseline.py` | artifact、builder 和脚本可复现性测试。 |

## 基线

- `prefetch_p95_ms`: `500`
- `top_k`: `8`
- `candidate_limit`: `64`
- `hnsw_ef_search`: `64`
- 本地合成样本：`128` 次，记录 `p95_ms=214`。

## 查询计划

- Personal query 使用 `idx_memory_embeddings_hnsw` 和 `idx_memory_items_scope_type_status`，并按 `subject_member_id` 隔离。
- Team query 使用同一 HNSW/过滤索引，并在候选集合后执行 `spicedb batch_check(memory#read_team)`。
- 当前 artifact 作为 P2 快速回归基线，P4 load test 需要替换为真实 PostgreSQL/pgvector/SpiceDB 指标。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_memory_performance_baseline.py
venv/bin/ruff check team_cloud/memory/performance.py scripts/team-cloud-memory-perf-baseline.py tests/team_cloud/test_memory_performance_baseline.py
venv/bin/python -m py_compile team_cloud/memory/performance.py scripts/team-cloud-memory-perf-baseline.py tests/team_cloud/test_memory_performance_baseline.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json
scripts/team-cloud-foundation-smoke.sh
```
