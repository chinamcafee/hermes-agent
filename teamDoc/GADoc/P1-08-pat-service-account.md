# P1-08 PAT 和 service account

日期：2026-05-22
状态：Implemented
前置：`P1-04 PostgreSQL 基础迁移`、`P1-07 Casdoor 同步 worker`

## 目标

本步骤落地 Team Cloud API token 的服务层：human PAT 和 service account token 均只保存 hash，支持 scope 白名单、过期、撤销、last used 更新和审计事件。当前实现使用内存 repository 固定行为契约，后续 API/DB 接入可替换 repository。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/auth/tokens.py` | token hash/verify、PAT/service account 签发、认证、撤销、审计。 |
| `team_cloud/auth/__init__.py` | 导出 token primitives。 |
| `tests/team_cloud/test_pat_service_accounts.py` | hash/redaction、scope、expiry、revocation、service account、owner 互斥测试。 |

## 行为

- Token hash：
  - 使用 PBKDF2-SHA256。
  - 每个 token 使用随机 salt。
  - 校验使用 constant-time compare。
  - 明文 token 只通过 `SecretStr` 返回一次，不进入 safe dict/repr。
- Human PAT：
  - 绑定 `owner_member_id`。
  - 保存 `org_id/scopes/expires_at/token_hash`。
  - 签发记录 `api_token.created` audit。
- Service account：
  - `create_service_account()` 绑定 `owner_member_id` 和 `org_id`。
  - service account token 绑定 `service_account_id`。
  - 签发后认证主体为 `actor_type=service_account`。
- 认证：
  - 校验 hash、revoked、expired、required scopes。
  - 成功后更新 `last_used_at`。
  - 缺失或不足 scope fail closed。
- 撤销：
  - `revoke_token()` 设置 `revoked_at`。
  - 记录 `api_token.revoked` audit。
  - `revoke_member_tokens()` 为 P1-07 disabled propagation 提供批量撤销入口。

## Scope 白名单

当前 P1-08 固定最小 scope 集：

- `chat:run`
- `memory:read`
- `memory:write`
- `tools:use`
- `admin:read`
- `admin:write`
- `service_accounts:manage`
- `service_accounts:use`

更细的工具风险、SpiceDB resource permission 和高危审批在 P3 工具权限工作包继续收紧。

## 非目标

- 不实现 FastAPI token endpoint。
- 不直接连接 PostgreSQL。
- 不实现 IP allowlist。
- 不做 SpiceDB permission check。
- 不实现 rate limit/quota。

## 后续衔接

- P1-09 到 P1-12：认证出的 token principal 进入 SpiceDB check 和 API permission gate。
- P1-13：组织/团队/成员 API 接入 PAT/service account 管理端点。
- P3-02 到 P3-04：工具调用根据 token scope、SpiceDB 和审批策略做最终授权。
