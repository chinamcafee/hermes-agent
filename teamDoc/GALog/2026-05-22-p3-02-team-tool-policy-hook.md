# P3-02 TeamToolPolicyHook 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-02。
- 将 P3-01 工具风险 taxonomy 接入 `pre_tool_call` 策略 hook。
- 调 SpiceDB `tool#*_execute` permission。
- 对 deny、SpiceDB error、缺失 team actor context fail closed。

## 执行记录

- 2026-05-22：在 P3-01 工具风险 taxonomy 完成并通过 foundation smoke 后启动 P3-02。
- 2026-05-22：读取 `hermes_cli.plugins.get_pre_tool_call_block_message()`、`model_tools.handle_function_call()`、`agent/tool_executor.py`、`team_cloud.authz.spicedb` 和 P3 规划，确认最小实现为 Team Cloud 策略核心 + inert-by-default repo plugin + hook context 透传。
- 2026-05-22：完成 `team_cloud.tool_policy`、`plugins/team_policy/`、
  `hermes_cli.plugins` hook 参数扩展，以及 agent 执行路径上下文
  helper 接入。
- 2026-05-22：新增 `teamDoc/GADoc/P3-02-team-tool-policy-hook.md`，
  并将 `tests/team_cloud/test_team_tool_policy_hook.py` 登记进
  foundation smoke 脚本和矩阵。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py`
  首次失败符合预期，5 个测试全部失败；主要缺口为
  `team_cloud.tool_policy` 不存在、`plugins/team_policy/plugin.yaml`
  不存在，以及 `get_pre_tool_call_block_message()` 尚未接收并透传
  `team_context/platform/user_id`。
- 红灯补充：加入 agent 侧 `pre_tool_call` 上下文 helper 测试后重跑，
  6 个测试全部失败；新增缺口为 `build_pre_tool_call_hook_kwargs`
  尚不存在。
- 绿灯：新增 `team_cloud.tool_policy.TeamToolPolicyHook`、env-gated
  `plugins/team_policy/`、`pre_tool_call` 团队上下文透传和 agent 侧
  共享上下文 helper 后，`scripts/run_tests.sh
  tests/team_cloud/test_team_tool_policy_hook.py` 通过，6 passed / 0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_platform_foundation_suite.py tests/team_cloud/test_team_tool_policy_hook.py`
  通过，9 passed / 0 failed。
- `venv/bin/ruff check team_cloud/tool_policy.py plugins/team_policy/__init__.py tests/team_cloud/test_team_tool_policy_hook.py hermes_cli/plugins.py agent/tool_dispatch_helpers.py agent/tool_executor.py agent/agent_runtime_helpers.py model_tools.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/tool_policy.py plugins/team_policy/__init__.py hermes_cli/plugins.py agent/tool_dispatch_helpers.py agent/tool_executor.py agent/agent_runtime_helpers.py model_tools.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，49 files / 182 tests
  passed / 0 failed。
