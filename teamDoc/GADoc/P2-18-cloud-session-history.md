# P2-18 云会话历史

日期：2026-05-22
状态：Implemented
前置：`P2-17 Web Chat 入口`

## 目标

本步骤为 Web Chat run 增加云会话历史写入和查询能力。P0 schema 已定义 `cloud_sessions`、`cloud_messages`、`cloud_tool_calls`；本步骤落地运行期最小模型和 API，使 Chat submit 能写入用户消息，runtime/tool 事件能写入 tool call 历史，并支持按组织、项目、成员和文本查询会话。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/cloud_sessions.py` | 本地 `InMemoryCloudSessionRepository`，管理 cloud session、message 和 tool call。 |
| `team_cloud/chat.py` | Chat run 创建时写入 cloud session 和首条 user message，并返回 `cloud_session_id`。 |
| `team_cloud/api.py` | 新增 cloud sessions 查询、详情和 tool call 写入 API。 |
| `tests/team_cloud/test_cloud_session_history.py` | 覆盖 Chat submit 写历史、列表过滤和 tool call 记录。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将云会话历史测试纳入平台 smoke。 |
| `teamDoc/GALog/2026-05-22-p2-18-cloud-session-history.md` | TDD 红绿记录和回归证据。 |

## API

`GET /api/cloud/sessions`

Query：

- `org_id`: organization 过滤，可选。
- `project_id`: project 过滤，可选。
- `member_id`: owner member 过滤，可选。
- `q`: title/message 文本过滤，可选。

Response：

- `items`: session summary 列表，含 `message_count` 和 `tool_call_count`。

`GET /api/cloud/sessions/{session_id}`

Response：

- session 全量对象。
- `messages`: cloud message 列表。
- `tool_calls`: cloud tool call 列表。

`POST /api/cloud/sessions/{session_id}/tool-calls`

Request：

- `org_id`: organization id。
- `run_id`: 关联 agent run id，可选。
- `actor_member_id`: actor/member id，可选。
- `tool_name`: 工具名。
- `risk_level`: `safe/network/file_read/file_write/terminal/destructive`。
- `decision`: `allowed/denied/approval_required/approved/rejected/error`。
- `input_redacted`: 脱敏后的工具输入。
- `output_redacted`: 脱敏后的工具输出，可选。
- `error`: 错误信息，可选。

## 行为

- `POST /api/chat/runs` 成功创建 run 时：
  - 创建 `cloud-session-*`。
  - 写入首条 `role=user` message。
  - run 响应带 `cloud_session_id`。
- `GET /api/cloud/sessions`：
  - 支持 org/project/member/q 组合过滤。
  - 默认按 `updated_at` 倒序返回。
- tool call 写入：
  - 校验 session 存在和 org_id 匹配。
  - 校验 risk/decision 枚举。
  - 详情查询返回 tool call 明细。

## 非目标

- 不实现数据库持久化 repository；P0/P1 已提供 schema，本步骤先落地本地运行模型。
- 不实现真实 runtime event bridge；P2-19 承接。
- 不实现搜索索引、导出和删除；P2 后续和 P3 治理阶段承接。

## 验证

- 红灯：Chat run 缺少 `cloud_session_id`，cloud sessions API 404，tool call 写入接口缺失。
- 绿灯：补齐 repository、API 和 Chat run 写入后，P2-18 焦点测试通过。
