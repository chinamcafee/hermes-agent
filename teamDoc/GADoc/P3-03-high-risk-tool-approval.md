# P3-03 高危工具审批

日期：2026-05-22
状态：Implemented
前置：`P3-02 TeamToolPolicyHook`

## 目标

本步骤在 P3-02 的 TeamToolPolicyHook 中加入高危工具 approval gate。执行顺序固定为：风险分类、Team actor 校验、SpiceDB check、Hermes approval、允许或 block。只有 P3-01 标记为 `terminal/destructive/secret` 的调用需要审批；safe/network/file 工具仍只受 SpiceDB permission 控制。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/tool_policy.py` | 增加 approval callback、默认 Hermes approval adapter、deny/timeout/missing gate block。 |
| `plugins/team_policy/__init__.py` | 启用插件时把默认 Hermes approval callback 注入 `TeamToolPolicyHook`。 |
| `tests/team_cloud/test_team_tool_policy_hook.py` | 覆盖 approval allow、deny、timeout、missing gate 和低风险不审批。 |
| `teamDoc/GALog/2026-05-22-p3-03-high-risk-tool-approval.md` | TDD 红绿记录和回归证据。 |

## 行为

- SpiceDB deny 优先于 approval，直接返回 `permission_denied`。
- SpiceDB allow 且风险为 `terminal/destructive/secret` 时触发 approval callback。
- approval 返回 `once/session/always/approve/allow/yes` 时允许本次工具调用。
- approval 返回 `deny` 或未知值时返回 `approval_denied` block。
- approval 返回 `timeout/timed_out/expired` 时返回 `approval_timeout` block。
- 高危调用没有可用 approval gate 或 callback 抛异常时返回 `approval_unavailable` block。
- safe/network/file 风险不触发 approval，避免额外打扰普通只读或低风险工作流。

## 默认 Adapter

`build_default_approval_callback()` 复用 Hermes `tools.approval.prompt_dangerous_approval()` 和 `tools.terminal_tool._get_approval_callback()`。对 terminal 工具，approval subject 使用真实 `command`；对其他高危工具，subject 使用 `tool_name + JSON args` 的截断摘要。插件仍由 `HERMES_TEAM_TOOL_POLICY_ENABLED` 控制，未启用时不改变本地默认行为。

## 非目标

- 不持久化 approval session/always 选择到 Team Cloud；P3-04 先落 audit，后续可按 org policy 增加 Team 级 approval cache。
- 不写 `cloud_tool_calls`；P3-04 承接 allow/deny/approval event 审计。
- 不改变 terminal_tool 现有危险命令 hardline block 和本地 approval 逻辑；Team Cloud approval 是企业权限层的额外 gate。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_team_tool_policy_hook.py
venv/bin/ruff check team_cloud/tool_policy.py plugins/team_policy/__init__.py tests/team_cloud/test_team_tool_policy_hook.py
venv/bin/python -m py_compile team_cloud/tool_policy.py plugins/team_policy/__init__.py tests/team_cloud/test_team_tool_policy_hook.py
scripts/team-cloud-foundation-smoke.sh
```
