# P4-07 Load test scripts 工作日志

## 背景

- 工作包：`P4-07 | Load test scripts | chat、prefetch、backup、permission check | P2/P3 | 2.5`
- 当前阶段：P4 Beta 验证，P4-01 到 P4-06 已完成。
- 设计依据：
  - P2-21 已提供 memory prefetch 性能基线。
  - P4 计划要求覆盖 chat runs、memory prefetch、SpiceDB check、embedding import、personal backup、org export、Gateway group session。

## 执行计划

1. 用 contract 测试定义 P4 load test plan 的场景、目标阈值、脚本和 artifact。
2. 新增 `team_cloud/load_testing.py` 和可执行生成脚本。
3. 新增 P4-07 文档和 JSON artifact。
4. 注册 foundation smoke，并运行红灯、绿灯、回归、静态检查和完整 smoke。

## 实时记录

- 2026-05-23：P4-07 已在进度表中标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-23：红灯验证已执行，`scripts/run_tests.sh tests/team_cloud/test_load_test_scripts.py` 出现 2 个预期失败，指向 `team_cloud.load_testing` 缺失和 load test artifact/docs/smoke 注册缺口。
- 2026-05-23：新增 `team_cloud/load_testing.py`、`scripts/team-cloud-load-test-plan.py`、P4-07 文档和 load test plan artifact，覆盖 7 个 Beta 负载场景。
- 2026-05-23：load test plan 生成脚本通过，`scripts/team-cloud-load-test-plan.py --output teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json` 输出 `status=written`。
- 2026-05-23：绿灯验证通过，`scripts/run_tests.sh tests/team_cloud/test_load_test_scripts.py` 结果为 1 个文件、2 个测试通过。
- 2026-05-23：相关回归通过，`scripts/run_tests.sh tests/team_cloud/test_load_test_scripts.py tests/team_cloud/test_memory_performance_baseline.py tests/team_cloud/test_platform_foundation_suite.py` 结果为 3 个文件、8 个测试通过。
- 2026-05-23：静态验证通过，`venv/bin/ruff check ...`、`venv/bin/python -m py_compile ...`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/load/team-cloud-load-test-plan-v0.json >/dev/null`、`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null` 和 `git diff --check ...` 均为 exit 0。
- 2026-05-23：完整 foundation smoke 通过，`scripts/team-cloud-foundation-smoke.sh` 结果为 75 个文件、259 个测试通过。
