# P3-03 高危工具审批工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-03。
- 在 P3-02 SpiceDB allow 之后，对 P3-01 判定为
  `terminal/destructive/secret` 的工具调用触发 Hermes approval。
- 对 approval deny 和 timeout 返回明确 block。
- 保持 P3-04 Tool audit 不在本步骤提前实现。

## 执行记录

- 2026-05-22：在 P3-02 完成并通过 foundation smoke 后启动 P3-03。
- 2026-05-22：读取 `tools.approval.prompt_dangerous_approval()`、
  `tools.terminal_tool` approval callback、P3 规划和 P3-02 文档，
  确认本步骤以可注入 approval gate 扩展 `TeamToolPolicyHook`。
- 2026-05-22：新增 `teamDoc/GADoc/P3-03-high-risk-tool-approval.md`，
  记录高危风险审批顺序、fail-closed 结果和非目标边界。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py`
  运行后 8 个测试中 3 个失败，符合预期；失败原因为
  `TeamToolPolicyHook.__init__()` 尚不支持 `approval_callback`，无法
  在 SpiceDB allow 后触发高危工具审批。
- 绿灯：`TeamToolPolicyHook` 增加 approval callback、deny/timeout/
  missing gate fail-closed、低风险不审批逻辑，`plugins/team_policy`
  默认接入 Hermes approval callback 后，`scripts/run_tests.sh
  tests/team_cloud/test_team_tool_policy_hook.py` 通过，8 passed /
  0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_platform_foundation_suite.py tests/team_cloud/test_team_tool_policy_hook.py`
  通过，11 passed / 0 failed。
- `venv/bin/ruff check team_cloud/tool_policy.py plugins/team_policy/__init__.py tests/team_cloud/test_team_tool_policy_hook.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/tool_policy.py plugins/team_policy/__init__.py tests/team_cloud/test_team_tool_policy_hook.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，49 files / 184 tests
  passed / 0 failed。
