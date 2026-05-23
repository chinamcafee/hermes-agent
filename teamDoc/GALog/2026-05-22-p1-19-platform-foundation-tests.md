# P1-19 平台基础测试工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-19。
- 固化平台基础 smoke 测试入口，覆盖 API、auth、authz、outbox、MinIO manifest、Web 管理壳。
- 增加跨管理 API、relationship outbox 和 permission explain 的集成回归。

## 执行记录

- 2026-05-22：启动 P1-19，读取 P1 工作包现有测试和 P1-19 交付要求。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_platform_foundation_suite.py`，覆盖 smoke matrix、脚本入口和集成回归。
- 2026-05-22：红灯确认后新增 `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` 和 `scripts/team-cloud-foundation-smoke.sh`。
- 2026-05-22：新增 `teamDoc/GADoc/P1-19-platform-foundation-tests.md`。
- 2026-05-22：首次运行 smoke 脚本发现漏掉 P1-07 Casdoor sync worker 测试，补入 matrix 和脚本后重跑。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_platform_foundation_suite.py`
  - 结果：`2 tests failed, 1 passed`。
  - 失败点：`teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` 和 `scripts/team-cloud-foundation-smoke.sh` 尚不存在；跨管理 API、relationship outbox 和 permission explain 的集成回归已具备当前行为。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_platform_foundation_suite.py`
  - 结果：`3 tests passed, 0 failed`。
- Smoke 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`91 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
