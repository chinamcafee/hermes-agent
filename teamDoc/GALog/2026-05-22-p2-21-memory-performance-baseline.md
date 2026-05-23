# P2-21 记忆性能基线工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P2-21。
- 为 memory prefetch、pgvector query plan 和 top-k/candidate limits 建立可重复的本地性能基线。
- 将 P95 目标、样本结果和调优建议写入 GADoc artifact。

## 执行记录

- 2026-05-22：在 P2-20 隔离测试套件完成并通过 foundation smoke 后启动 P2-21。
- 2026-05-22：确认 P2-21 需要输出性能基线文档和可测试 artifact，不依赖外部数据库即可在本地快速回归。
- 2026-05-22：新增 `team_cloud/memory/performance.py`，从既有 `explain_pgvector_query()` 生成 personal/team_shared 查询计划。
- 2026-05-22：新增 `scripts/team-cloud-memory-perf-baseline.py`，可重复写入 `memory-performance-baseline-v0.json`。
- 2026-05-22：新增 `teamDoc/GADoc/P2-21-memory-performance-baseline.md`，记录 P95 目标、调优参数、查询计划和后续 P4 live load test 衔接。
- 2026-05-22：将 `tests/team_cloud/test_memory_performance_baseline.py` 纳入 foundation smoke 脚本和 matrix。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_memory_performance_baseline.py`
  - 结果：`1 files, 0 passed, 3 failed`。
  - 失败点：缺少 `memory-performance-baseline-v0.json`、`team_cloud.memory.performance` 和 `scripts/team-cloud-memory-perf-baseline.py`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_memory_performance_baseline.py`
  - 结果：`1 files, 3 tests passed, 0 failed`。

## 回归验证

- `venv/bin/ruff check team_cloud/memory/performance.py scripts/team-cloud-memory-perf-baseline.py tests/team_cloud/test_memory_performance_baseline.py`
  - 结果：`All checks passed!`
- `venv/bin/python -m py_compile team_cloud/memory/performance.py scripts/team-cloud-memory-perf-baseline.py tests/team_cloud/test_memory_performance_baseline.py`
  - 结果：exit 0。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/memory-performance-baseline-v0.json`
  - 结果：JSON 解析成功。
- `scripts/team-cloud-foundation-smoke.sh`
  - 结果：`45 files, 167 tests passed, 0 failed`。
