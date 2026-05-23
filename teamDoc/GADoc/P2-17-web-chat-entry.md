# P2-17 Web Chat 入口

日期：2026-05-22
状态：Implemented
前置：`P2-14 AIAgent.team_context`、`P2-16 Gateway identity resolver`

## 目标

本步骤在 Team Web Console 中增加最小 Chat 入口，并在 Team Cloud API 中提供 agent run 创建与事件查看接口。Chat submit 必须先走 SpiceDB `chat.run` 权限校验，只有允许 `project#run_agent` 的 member 才能创建 run。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/chat.py` | `InMemoryChatRunService`，提供本地 agent run 创建和事件列表。 |
| `team_cloud/api.py` | 新增 `POST /api/chat/runs` 和 `GET /api/chat/runs/{run_id}/events`。 |
| `deploy/team-cloud/web-shell/index.html` | 新增 Chat tab、submit form、run status、event viewer 和错误态。 |
| `tests/team_cloud/test_web_chat_entry.py` | 覆盖权限校验、run 创建、事件查看和 Web Shell wiring。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 Web Chat 入口测试纳入平台 smoke。 |
| `teamDoc/GALog/2026-05-22-p2-17-web-chat-entry.md` | TDD 红绿记录和回归证据。 |

## API

`POST /api/chat/runs`

Request：

- `org_id`: organization id。
- `team_id`: team id。
- `project_id`: project id，作为 `chat.run` 权限检查的 resource。
- `member_id`: 当前 actor/member id，作为 `user:<member_id>` subject。
- `message`: 用户提交给 Hermes runtime 的消息。

Response：

- `id`: agent run id。
- `status`: 初始为 `queued`。
- `org_id/team_id/project_id/member_id/message`: 归一化后的 run 上下文。
- `events`: 初始事件列表，包含 `chat.run.created` 和 `chat.message.accepted`。

`GET /api/chat/runs/{run_id}/events`

Response：

- `items`: run event 列表，按 sequence 升序返回。

## 权限行为

- `authz_client` 未配置：返回 `403 authz_client_not_configured`。
- SpiceDB check 抛错：返回 `403 authorization_unavailable`。
- SpiceDB deny：返回 `403 permission_denied`。
- SpiceDB allow：
  - 创建 `queued` run。
  - 写入初始事件。
  - Web Console 可立即展示 run status 和 event viewer。

## Web 行为

- Chat tab 与 Teams/Members/Roles/Permission 共用组织上下文。
- Submit 表单要求 team、project、member 和 message。
- 成功后展示 run id/status/org/team/project/member，并加载事件列表。
- 失败时保留面板级 `chat-error`，不影响其他 admin tabs。

## 非目标

- 不持久化 `cloud_sessions`、`cloud_messages`、`cloud_tool_calls`；P2-18 承接。
- 不桥接真实 Hermes runtime streaming；P2-19 承接 runtime event bridge。
- 不实现 Chat 历史搜索、导出和删除；P2-18 后续承接。

## 验证

- 红灯：`POST /api/chat/runs` 404、事件查看缺少 run id、Web Shell 缺少 Chat surfaces。
- 绿灯：补齐 chat service、API routes 和 Web Shell Chat tab 后，P2-17 焦点测试通过。
