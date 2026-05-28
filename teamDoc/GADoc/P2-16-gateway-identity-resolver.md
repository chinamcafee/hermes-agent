# P2-16 Gateway identity resolver

日期：2026-05-22
状态：Implemented
前置：`P2-15 API Server identity headers`

## 目标

本步骤为 Gateway 平台消息进入 Hermes Agent 前增加 Team Cloud external identity resolve。Gateway 不直接把平台 user id 当企业身份；它先调用 Team Cloud 解析 org/team/project/member，再用解析结果隔离 session key、agent cache 和双层记忆注入语义。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/internal/httpapi/server.go` | Team Cloud external identity / auth/session 相关 API 的 Go HTTP 入口。 |
| `gateway/team_identity.py` | Gateway 侧 resolver client、配置解析、resolve 响应归一化和 session key prefix helper。 |
| `gateway/session.py` | `SessionSource.team_context` 序列化和基于 org/team 的 session key 前缀隔离。 |
| `gateway/run.py` | 在 `_handle_message()` 进入 agent 前解析团队身份，并把 `team_context` 传入 `_run_agent()`、proxy 和 `AIAgent(...)`。 |
| `team_cloud/internal/httpapi/server.go` | prefetch 忽略 `include_personal`，当前 GA 主路径只返回 `team_shared`。 |
| `agent/team_memory_provider.py` | `TeamContext.personal_memory_enabled` 固定不再启用云端 personal partition。 |
| `team_cloud/internal/httpapi/cli_auth_test.go` | 覆盖成员登录/session API。 |
| `tests/gateway/test_gateway_team_identity_resolver.py` | 覆盖 Gateway session key prefix、绑定提示、parse 兼容和 `AIAgent.team_context` 透传。 |
| `teamDoc/GALog/2026-05-22-p2-16-gateway-identity-resolver.md` | TDD 红绿记录和回归证据。 |

## 配置契约

Gateway identity resolver 支持 `config.yaml` 和环境变量两种启用方式：

```yaml
gateway:
  team_identity:
    enabled: true
    team_cloud_url: "http://127.0.0.1:8780"
    auth_mode: "member_token"
    member_token: "${HERMES_TEAM_CLOUD_MEMBER_TOKEN}"
```

环境变量：

| 变量 | 用途 |
| --- | --- |
| `HERMES_GATEWAY_TEAM_IDENTITY_ENABLED` | 显式启停 resolver。 |
| `HERMES_TEAM_CLOUD_URL` | Team Cloud base URL。 |
| `HERMES_TEAM_CLOUD_MEMBER_TOKEN` | Gateway 调 Team Cloud API 的成员级 session token、OIDC/JWT 或后续 PAT。 |

如果配置缺失但显式启用，Gateway fail closed，返回团队身份解析失败提示，不创建 Agent。

## 行为

- Gateway 在平台 allowlist/pairing 通过后、创建 agent 前执行身份解析。
- Team Cloud resolve 返回 `resolved`：
  - Gateway 将 `team_context` 写入 `SessionSource` 和 `MessageEvent`。
  - session key 增加 `team:<encoded_org_id>:<encoded_team_id>:` 前缀。
  - agent cache signature 纳入 `team_context`，避免跨团队复用 cached agent。
  - 本地 Agent 创建和 proxy 模式均透传 Team identity。
- Team Cloud resolve 返回 `unbound`：
  - Gateway 返回绑定提示。
  - 不生成 session key sentinel，不创建 `AIAgent`。
- shared multi-user session：
  - `personal_memory_enabled=False`。
  - Team memory provider 不再请求云端 personal partition。
  - Team Cloud prefetch 固定只返回 `team_shared`。
- `_parse_session_key()` 会剥离 `team:<org>:<team>:` 前缀，保留现有平台路由解析能力。

## 非目标

- 不实现绑定码签发、确认和持久化存储；本步骤只落地 runtime resolver 边界和最小本地实现。
- 不新增 in-tree `plugins/memory/*` provider，延续 P2-11 决策。
- 不实现 Web Chat 入口和云会话历史；P2-17、P2-18 承接。

## 验证

- 红灯：缺少 `team_cloud.identity`、缺少 `gateway.team_identity`、`GatewayRunner._run_agent()` 不接受 `team_context`。
- 补充红灯：`MemoryPrefetchPipeline.prefetch()` 不接受 `include_personal`。
- 绿灯：补齐 Team Cloud resolve API、Gateway resolver、session key 前缀、`team_context` 透传和 personal memory 禁用后，P2-16 焦点测试通过。
