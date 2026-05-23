# P3-19 AuthZ chaos tests 工作日志

## 背景

- 工作包：`P3-19 | AuthZ chaos tests | SpiceDB outage、outbox lag、dead letter fail closed | P3-02 | 2`
- 当前阶段：P3 数据治理与权限硬化，P3-01 到 P3-18 已完成。
- 设计依据：
  - `teamDoc/05-auth-permission-design.md`：SpiceDB outbox 超过阈值进入 dead letter 后，相关资源 fail closed。
  - `teamDoc/08-risks-and-validation.md`：SpiceDB 不可用时默认拒绝管理和高危读写；relationship outbox 未完成时危险操作 fail closed。
  - `teamDoc/GAStep/04-phase-3-governance-steps.md`：对 outbox lag、dead letter、permission deny spike 做告警/解释能力。

## 执行计划

1. 复核 AuthZ middleware、SpiceDB client、relationship outbox、tool policy 与 permission explorer 的现有 fail-closed 行为。
2. 以 TDD 新增 `tests/team_cloud/test_authz_chaos.py`，覆盖：
   - 管理 API 在 SpiceDB outage 下 fail closed。
   - Chat run 在 SpiceDB outage 下 fail closed。
   - 高危工具在 SpiceDB outage 下 fail closed，并记录 `authorization_unavailable`。
   - outbox pending/dead_letter 对相关资源 fail closed，并在权限解释中暴露 deny reason。
3. 如红灯测试暴露缺口，最小化补齐 AuthZ chaos 检测/摘要能力。
4. 将新测试纳入 foundation smoke 矩阵和平台 suite 断言。
5. 运行单测、相关回归、ruff、py_compile、JSON 校验、foundation smoke 和 diff whitespace 检查。

## 实时记录

- 2026-05-22：P3-19 标记为 In Progress，开始按 TDD 红绿循环推进。
- 2026-05-22：红灯测试已创建并运行
  `scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py`；结果为
  5 个测试中 2 个通过、3 个失败。失败根因：
  - AuthZ middleware 在 `SpiceDBClient(fail_closed=True)` 返回
    `reason=spicedb_error` 时仍输出 `permission_denied`。
  - Chat run 权限检查在同一 outage 场景下仍输出 `permission_denied`。
  - Relationship outbox 缺少区分 pending lag 和 dead letter 的 fail-closed
    状态摘要。
- 2026-05-22：绿灯实现完成并重跑
  `scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py`；结果为
  1 个测试文件、5 个测试通过、0 失败。
- 2026-05-22：新增 `teamDoc/GADoc/P3-19-authz-chaos-tests.md`，并将
  `tests/team_cloud/test_authz_chaos.py` 纳入 foundation smoke 矩阵、
  smoke 脚本和 `test_platform_foundation_suite.py` 覆盖断言。

## 验证记录

- `scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py`：1 个测试文件、5 个测试通过、0 失败。
- `scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py`：7 个测试文件、31 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/authz/middleware.py team_cloud/authz/outbox.py team_cloud/api.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/authz/middleware.py team_cloud/authz/outbox.py team_cloud/api.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- `scripts/team-cloud-foundation-smoke.sh`：65 个测试文件、229 个测试通过、0 失败。
- `git diff --check -- ...P3-19 touched files...`：通过。

## 完成记录

- 2026-05-22：P3-19 AuthZ chaos tests 已完成，P3 完成人周更新为
  `51.0 / 56.5`，完成率 `90.3%`；下一项为 P3-20 数据治理文档。
