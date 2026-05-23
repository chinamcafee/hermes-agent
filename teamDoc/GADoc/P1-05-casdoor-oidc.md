# P1-05 Casdoor OIDC 接入

日期：2026-05-22
状态：Implemented
前置：`P0-06 Casdoor OIDC 验证`、`P1-03 本地 compose 栈`

## 目标

本步骤实现 Team Cloud 侧 Casdoor OIDC client 和最小 API 路由。范围包含 authorization code URL、token exchange、OIDC discovery、JWKS cache、key rotation 和 id_token 验证。P1-06 继续实现 JWT middleware、member status fail-closed 和 API 保护。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/auth/oidc.py` | Casdoor OIDC client、TokenSet、verification error。 |
| `team_cloud/auth/__init__.py` | auth package 导出。 |
| `team_cloud/api.py` | `/auth/oidc/authorize` 和 `/auth/oidc/callback` 最小路由。 |
| `tests/team_cloud/test_casdoor_oidc.py` | authorize/token/JWKS/id_token/API route 测试。 |

## 验证规则

`CasdoorOIDCClient.verify_id_token()` 校验：

- discovery issuer。
- configured audience/client id。
- `RS256` 签名。
- `exp`、`nbf`、`iat`、`iss`、`aud`、`sub` 必填。
- 可选 nonce 匹配。
- unknown `kid` 时刷新 JWKS，用于 key rotation。

## API 路由

- `GET /auth/oidc/authorize` 返回 authorization URL、state、nonce。当前不保存 session，P1-16 Web 登录壳会接入浏览器 session。
- `GET /auth/oidc/callback` 使用 authorization code 换 token，验证 id_token，只返回非敏感 subject/email/name/state，不返回 token。

## 非目标

- 不实现 JWT middleware。
- 不做 member status fail-closed。
- 不把 Casdoor roles/groups 当最终授权。
- 不保存 refresh token 或浏览器 session。
