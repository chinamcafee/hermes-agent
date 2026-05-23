# P2-20 隔离测试套件工作日志

日期：2026-05-22
状态：Done

## 目标

- 按 `GAStep` 顺序推进 P2-20。
- 建立覆盖 personal/team_shared、org/team、Gateway identity、Web Chat/cloud history 的隔离测试套件。
- 把隔离测试纳入可重复执行的 smoke/CI 脚本。

## 执行记录

- 2026-05-22：在 P2-19 Runtime event bridge 完成并通过 foundation smoke 后启动 P2-20。
- 2026-05-22：确认 P2-20 需要沉淀跨模块隔离断言，避免 P2 已完成能力在后续 P3/P4 中回归。
- 2026-05-22：新增 `scripts/team-cloud-isolation-smoke.sh`，聚合 memory isolation、Gateway identity、API trusted headers、cloud history 和 runtime event bridge 测试。
- 2026-05-22：新增 `teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json`，记录 P2 隔离验收域和验证命令。
- 2026-05-22：新增 `tests/team_cloud/test_isolation_suite.py`，校验隔离脚本和矩阵覆盖必要边界。
- 2026-05-22：将 `tests/team_cloud/test_isolation_suite.py` 纳入 foundation smoke script 和 platform foundation suite 断言。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py`
  - 结果：`1 files, 0 tests passed, 2 failed`。
  - 失败点：缺少 `scripts/team-cloud-isolation-smoke.sh` 和 `teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py`
  - 结果：`1 files, 2 tests passed, 0 failed`。

## 回归验证

- 回归：`venv/bin/python -m json.tool teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json >/dev/null && venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  - 结果：退出码 0。
- 回归：`venv/bin/ruff check tests/team_cloud/test_isolation_suite.py`
  - 结果：`All checks passed!`。
- 回归：`venv/bin/python -m py_compile tests/team_cloud/test_isolation_suite.py`
  - 结果：退出码 0。
- 回归：`scripts/team-cloud-isolation-smoke.sh`
  - 结果：`11 files, 37 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/team_cloud/test_isolation_suite.py tests/team_cloud/test_platform_foundation_suite.py tests/team_cloud/test_deployment_docs.py`
  - 结果：`3 files, 7 tests passed, 0 failed`。
- 回归：`scripts/team-cloud-foundation-smoke.sh`
  - 结果：`44 files, 164 tests passed, 0 failed`。
