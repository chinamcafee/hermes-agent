# P3-13 Retention policies 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-13。
- 定义 session、tool_call、memory、audit_event 的保留策略 contract。
- 支持保留天数、动作、legal hold 跳过和到期计划。
- 支持在 in-memory repository 上应用策略，为后续 worker/后台任务替换真实 repository 留出边界。

## 执行记录

- 2026-05-22：P3-12 完成并通过 foundation smoke 后启动 P3-13。
- 2026-05-22：读取 `teamDoc/06-cloud-data-management.md`、`teamDoc/08-risks-and-validation.md`、`teamDoc/12-ga-product-requirements.md` 和 P3-07/P3-12 文档，确认 P3-13 聚焦保留策略计算和清理 contract。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_retention_policies.py`
  失败符合预期，3 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.retention'`。
- 绿灯：实现 `team_cloud/retention.py` 后重跑
  `scripts/run_tests.sh tests/team_cloud/test_retention_policies.py`，
  1 个测试文件、3 个测试通过、0 失败。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_retention_policies.py
  tests/team_cloud/test_platform_foundation_suite.py`：2 个测试文件、6 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/retention.py
  tests/team_cloud/test_retention_policies.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/retention.py
  tests/team_cloud/test_retention_policies.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool
  teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- `scripts/team-cloud-foundation-smoke.sh`：59 个测试文件、209 个测试通过、0 失败。

## 完成记录

- 2026-05-22：P3-13 Retention policies 已完成，foundation smoke 纳入
  `retention_policies` domain；P3-14 break-glass 承接双人审批临时访问。
