# P2-15 API Server identity headers

日期：2026-05-22
状态：Implemented
前置：`P2-14 AIAgent.team_context`

## 目标

本步骤为 OpenAI-compatible API Server 增加 Team Cloud 可信 identity headers。API Server 只在 Team Cloud service token 校验通过后接受企业身份上下文，并把解析出的 `team_context` 传入 Hermes `AIAgent`。

## 工件

| 工件 | 用途 |
| --- | --- |
| `gateway/platforms/api_server.py` | 解析 trusted headers、校验 service token、透传 `team_context`、更新 CORS/capabilities。 |
| `tests/gateway/test_api_server_team_headers.py` | 覆盖未配置 token 拒绝、无效 token 拒绝、有效 token 透传和 `_create_agent()` 传参。 |
| `teamDoc/GALog/2026-05-22-p2-15-api-server-identity-headers.md` | TDD 红绿记录和回归证据。 |

## Header 契约

| Header | 必填 | 用途 |
| --- | --- | --- |
| `X-Hermes-Team-Cloud-Token` | 是 | Team Cloud service token。 |
| `X-Hermes-Org-Id` | 是 | Team Cloud organization id。 |
| `X-Hermes-Team-Id` | 是 | Team Cloud team id。 |
| `X-Hermes-Member-Id` | 是 | 当前 actor/member id。 |
| `X-Hermes-Project-Id` | 否 | 当前 project id。 |

## 行为

- 如果请求不带任何 Team identity header：
  - API Server 保持旧行为，不注入 `team_context`。
- 如果请求带 Team identity header 但 API Server 未配置 `team_cloud_service_token`：
  - 返回 `403 team_identity_not_configured`。
- 如果请求带 Team identity header 但 service token 缺失或不匹配：
  - 返回 `401 invalid_team_cloud_service_token`。
- 如果 service token 通过：
  - 要求 `org_id/team_id/member_id` 均存在。
  - 拒绝 CR/LF/NUL 和过长 header。
  - 生成 `team_context` 并传入 `_run_agent()`、`_create_agent()` 和最终 `AIAgent(...)`。
- CORS/capabilities：
  - CORS allow headers 增加 Team identity header。
  - `/v1/capabilities` 暴露 header 名和 `team_identity_headers_enabled`。

## 非目标

- 不实现 Gateway platform identity resolver；P2-16 承接。
- 不实现 session key 的 org/team 前缀；P2-16 承接。
- 不替代 Team Cloud 侧 Casdoor/JWT/PAT/service-account 校验；本步骤只验证 API Server 接受 trusted injection 的最小 gate。

## 验证

- 红灯：trusted headers 被忽略、`team_context` 未传给 `_run_agent()`、`_create_agent()` 不接受 `team_context`。
- 绿灯：补齐 service-token gate、header 解析和 agent 创建透传后，P2-15 焦点测试通过。
