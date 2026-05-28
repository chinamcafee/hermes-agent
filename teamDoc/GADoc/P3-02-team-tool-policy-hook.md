# P3-02 TeamToolPolicyHook

日期：2026-05-22
状态：Implemented
前置：`P3-01 工具风险 taxonomy`

## 目标

本步骤把 P3-01 的工具风险分类接入 Hermes `pre_tool_call` hook，并通过 Team Cloud SpiceDB 权限做 fail-closed 拦截。P3-02 只负责工具执行前授权，暂不实现高危审批和 `cloud_tool_calls` 审计写表；审批由 P3-03 承接，工具审计由 P3-04 承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `agent/team_tool_policy.py` | `TeamToolPolicyHook`、风险到 permission 映射、Team actor 解析。旧 Python `team_cloud.tool_policy` 已退役。 |
| `plugins/team_policy/` | repo-shipped env-gated policy plugin，注册 `pre_tool_call`。 |
| `hermes_cli/plugins.py` | `get_pre_tool_call_block_message()` 支持透传 `team_context/platform/user_id`。 |
| `agent/tool_dispatch_helpers.py` | agent-owned tool path 的共享 pre hook 上下文构造。 |
| `agent/tool_executor.py` | concurrent/sequential 工具执行路径透传 Team Cloud 上下文。 |
| `agent/agent_runtime_helpers.py` | agent-loop 直连工具执行路径透传 Team Cloud 上下文。 |
| `tests/team_cloud/test_team_tool_policy_hook.py` | deny、SpiceDB error、缺失 actor、hook 透传和插件登记测试。 |

## 权限映射

| 风险/工具 | SpiceDB permission |
| --- | --- |
| `safe` | `safe_execute` |
| `network` | `network_execute` |
| `read_file` / `search_files` / `vision_analyze` | `file_read_execute` |
| `write_file` / `patch` / `skill_manage` / `image_generate` / `text_to_speech` | `file_write_execute` |
| `terminal` | `terminal_execute` |
| `destructive` / `secret` | `destructive_execute` |

## Fail-Closed 行为

- 缺少 `team_context.member_id`、`actor_id`、`user_id` 或 service account 标识时，返回 `team_actor_missing` block。
- policy plugin 已启用但无可用 authz client 时，返回 `authorization_unavailable` block。
- SpiceDB check 抛异常或返回 `spicedb_error` 时，返回 `authorization_unavailable` block。
- SpiceDB deny 时，返回 `permission_denied` block。
- 允许时返回 `None`，保持现有 Hermes tool execution 行为。

## 插件启用

`plugins/team_policy` 为 bundled backend 插件，加载后只有在 `HERMES_TEAM_TOOL_POLICY_ENABLED` 为 truthy 时才注册 hook。这样本地普通运行默认不改变行为；企业运行如果启用策略但 authz client 未接通，会 fail closed，避免无意放行。

## 非目标

- 不触发 Hermes approval flow；P3-03 实现高危工具审批。
- 不写 `cloud_tool_calls` 和 audit；P3-04 实现工具审计。
- 不在 `run_agent.py` 或 `model_tools.py` 写死 Team Cloud 业务逻辑；策略逻辑集中在 `agent.team_tool_policy` 和插件 hook。
- 不新增 SpiceDB 网络 transport；P1 的 `SpiceDBClient` 抽象作为注入边界，本步骤只定义 hook contract。

## 验证

```bash
venv/bin/python -m pytest tests/hermes_cli/test_team_tool_policy.py -q
venv/bin/python -m py_compile agent/team_tool_policy.py plugins/team_policy/__init__.py hermes_cli/plugins.py agent/tool_dispatch_helpers.py agent/tool_executor.py agent/agent_runtime_helpers.py model_tools.py
scripts/team-cloud-foundation-smoke.sh
```
