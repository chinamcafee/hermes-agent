# P3-11 删除请求工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-11。
- 支持 member/project/org 删除请求。
- 支持 `anonymize`、`soft_delete`、`hard_delete` 模式。
- 支持删除前绑定 org export。
- 支持审批、scheduled execution 和 audit。
- 不在本步骤执行 PostgreSQL/SpiceDB/MinIO hard delete；P3-12 承接。

## 执行记录

- 2026-05-22：在 P3-10 完成并通过 foundation smoke 后启动 P3-11。
- 2026-05-22：读取数据删除规划和 audit/outbox contract，确认最小实现为
  in-memory deletion request service。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_deletion_request.py`
  失败符合预期，2 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.deletion'`。
- 绿灯：实现 `team_cloud/deletion.py` 后重跑
  `scripts/run_tests.sh tests/team_cloud/test_deletion_request.py`，
  1 个测试文件、2 个测试通过、0 失败。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_deletion_request.py
  tests/team_cloud/test_platform_foundation_suite.py`：2 个测试文件、5 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/deletion.py
  tests/team_cloud/test_deletion_request.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/deletion.py
  tests/team_cloud/test_deletion_request.py
  tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool
  teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- `scripts/team-cloud-foundation-smoke.sh`：57 个测试文件、204 个测试通过、0 失败。

## 完成记录

- 2026-05-22：P3-11 删除请求已完成，foundation smoke 纳入
  `deletion_request` domain；P3-12 hard delete worker 承接真实清理。
