# P1-06 JWT 中间件

日期：2026-05-22
状态：Implemented
前置：`P1-05 Casdoor OIDC 接入`

## 目标

本步骤把 P1-05 的 OIDC verifier 接入 Team API request path。中间件负责 Bearer token 提取、id_token/JWT 验证、member status fail-closed 和 principal 注入。真实 DB member resolver 与 Casdoor 同步 worker 留给 P1-07。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/auth/middleware.py` | JWT middleware、`TeamPrincipal`、public path 列表。 |
| `team_cloud/api.py` | 可选启用 middleware，并提供 `/api/whoami` 受保护端点。 |
| `tests/team_cloud/test_jwt_middleware.py` | 401/403/active principal/public path 覆盖。 |

## 行为

- Public path：`/healthz`、`/readyz`、`/auth/oidc/authorize`、`/auth/oidc/callback`、docs endpoints。
- Missing Bearer：`401` + `WWW-Authenticate: Bearer`。
- Invalid token：`401`，不暴露 token 内容。
- Non-active member：`403 member_not_active`。
- Active member：`request.state.principal` 注入 `subject/email/name/member_status/claims`。

## 非目标

- 不查询真实 PostgreSQL member 表。
- 不同步 Casdoor disabled user。
- 不签发 PAT/service account token。
- 不做 endpoint-level SpiceDB authorization。
