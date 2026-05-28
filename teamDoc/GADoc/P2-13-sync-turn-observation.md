# P2-13 sync_turn observation

日期：2026-05-22
状态：Implemented
前置：`P2-11 TeamMemoryProvider 插件`

## 目标

本步骤补齐 Hermes turn observation ingestion，使 `TeamMemoryProvider.sync_turn()` 发出的 `/v1/memory/observations` payload 可以被 Team Cloud API 接收、校验并写入 observation repository，供 P2-07 extraction worker 消费。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/internal/httpapi/server.go` | Go Team Cloud `POST /v1/memory/observations` 接入。 |
| `agent/team_memory_provider.py` | `sync_turn()` 可选透传 `turn_metadata` 和 `tool_summaries`。 |
| `team_cloud/internal/httpapi/server_test.go` | 覆盖 observation API、metadata/tool summaries 和 context fencing。 |
| `tests/hermes_cli/test_team_memory_provider.py` | 覆盖 provider `sync_turn()` metadata/tool summaries 透传。 |
| `teamDoc/GALog/2026-05-22-p2-13-sync-turn-observation.md` | TDD 红绿记录和回归证据。 |

## 行为

- `create_app(memory_observation_repository=...)`：
  - 注入 observation repository。
  - 启用 `POST /v1/memory/observations`。
- `POST /v1/memory/observations`：
  - 接收 `org_id/session_id/member_id/team_id/project_id/observation`。
  - 将 observation 写为 `pending`，交给 extraction worker 后续处理。
  - 保留 `turn_metadata`，例如 run id、model、turn number。
  - 保留 `tool_summaries`，例如 tool name、status、memory ids。
  - 注入 canonical `context`，包含 org/session/member/team/project。
- Context fencing：
  - 如果 observation 自带 `context`，其中任一非空字段与 top-level canonical context 不一致，则返回 `400`。
  - 该 fence 防止 provider 或上游 runtime 把 Bob/Alice、org/team/project 语境混写到同一条 observation。
- `TeamMemoryProvider.sync_turn()`：
  - 旧调用保持兼容，只发 `source` 和 user/assistant messages。
  - 调用方传入 `turn_metadata` 或 `tool_summaries` 时，将其写入 observation payload。

## 非目标

- 不接入 `AIAgent.team_context`；P2-14 承接。
- 不从 Hermes runtime 自动提取 tool summaries；P2-19 runtime event bridge 承接。
- 不实现 cloud sessions/messages/tool_calls 持久化；P2-18 承接。

## 验证

- 红灯：observation API 测试因 app factory 缺少 `memory_observation_repository` 参数失败。
- 红灯：provider metadata 测试因 `sync_turn()` 缺少 `turn_metadata` 参数失败。
- 绿灯：补齐 API endpoint、context fence 和 provider optional metadata 后，两组焦点测试通过。
