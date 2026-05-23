# P2-14 AIAgent.team_context

日期：2026-05-22
状态：Implemented
前置：`P1-01 Team Cloud repo/package 骨架`

## 目标

本步骤为 Hermes runtime 增加 `AIAgent.team_context` 初始化入口，并将该上下文透传给 memory provider 初始化链。这样后续 Team Cloud memory provider、API Server identity headers、Gateway identity resolver 能共享同一组 org/team/project/member 语境。

## 工件

| 工件 | 用途 |
| --- | --- |
| `run_agent.py` | `AIAgent.__init__` 新增可选 `team_context` 参数并转发给 `init_agent()`。 |
| `agent/agent_init.py` | 保存 `agent.team_context`，并在 memory provider `initialize()` kwargs 中透传非空 team context。 |
| `tests/run_agent/test_memory_provider_init.py` | 覆盖 team_context 透传和未配置时的向后兼容。 |
| `teamDoc/GALog/2026-05-22-p2-14-aiagent-team-context.md` | TDD 红绿记录和回归证据。 |

## 行为

- `AIAgent(..., team_context=...)`：
  - 接受 dict-like context，不要求 Team Cloud 代码被 core runtime import。
  - 将值保存为 `agent.team_context`。
  - memory provider 激活时把该值放入 `initialize(..., team_context=...)`。
- `AIAgent(...)` 未传 `team_context`：
  - `agent.team_context` 为 `None`。
  - memory provider initialize kwargs 不包含 `team_context`，避免旧 provider 因未知语义产生行为变化。
- memory provider 初始化链：
  - 保持原有 `session_id/platform/hermes_home/user_id/chat_id/gateway_session_key/agent_identity` 透传逻辑。
  - 仅在 `team_context is not None` 时增加字段。

## 非目标

- 不实现 API Server trusted identity headers；P2-15 承接。
- 不实现 Gateway external identity resolve；P2-16 承接。
- 不在 core runtime 中 import `team_cloud.memory.TeamContext`；保持 core 与 Team Cloud package 的边界清晰。

## 验证

- 红灯：`AIAgent.__init__` 缺少 `team_context` 参数，旧路径也没有默认 `agent.team_context` 属性。
- 绿灯：补齐参数、属性和 provider initialize kwargs 后，`tests/run_agent/test_memory_provider_init.py` 通过。
