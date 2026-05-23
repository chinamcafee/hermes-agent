# P0-06 Casdoor OIDC 验证

日期：2026-05-22
状态：Validated for P0 execution
前置：`P0-05 本地拓扑设计`

## 目标

验证冻结版本 Casdoor 能完成 OIDC discovery、签发 `id_token`，并由 Team Cloud 侧逻辑验证 `issuer`、`audience`、`signature`、`exp`。本步骤是协议烟测，不代表生产登录流最终形态。

## 验证环境

| 项 | 值 |
| --- | --- |
| 镜像 | `casbin/casdoor-all-in-one:3.60.1` |
| 用途 | 临时本地 OIDC 烟测；P1 compose 仍按 P0-05 使用 `casbin/casdoor:3.60.1` + PostgreSQL。 |
| 本地地址 | `http://localhost:18000` |
| Discovery endpoint | `http://localhost:18000/.well-known/openid-configuration` |
| JWKS endpoint | `http://localhost:18000/.well-known/jwks` |
| token endpoint | `http://localhost:18000/api/login/oauth/access_token` |
| 签名算法 | `RS256` |
| `kid` | `cert-built-in` |

为便于自动化拿 token，本次临时容器只对内置 application 开启了 password grant。该偏差只用于 P0-06 烟测；GA 登录路径必须使用 authorization code + PKCE，不能把 password grant 作为 Team Web 默认路径。

## Discovery 结果

```json
{
  "issuer": "http://localhost:18000",
  "authorization_endpoint": "http://localhost:18000/login/oauth/authorize",
  "token_endpoint": "http://localhost:18000/api/login/oauth/access_token",
  "jwks_uri": "http://localhost:18000/.well-known/jwks"
}
```

## Token 验证结果

验证命令使用 `PyJWT` 的 `PyJWKClient` 拉取 JWKS，并要求：

- `alg` 为 `RS256`。
- `iss` 等于 `http://localhost:18000`。
- `aud` 包含本地 application client id。
- `exp`、`iat`、`iss`、`aud`、`sub` 必须存在。
- 使用 JWKS 中 `kid=cert-built-in` 的公钥完成签名验证。

非敏感 claim 摘要：

```json
{
  "verified": true,
  "algorithm": "RS256",
  "kid": "cert-built-in",
  "issuer": "http://localhost:18000",
  "audience": [
    "5d17b05caf9b4295b1c9"
  ],
  "subject": "f2bcb55b-f488-4389-a64e-56e5cefaefae",
  "name": "admin",
  "email": "admin@example.com",
  "checks": [
    "issuer",
    "audience",
    "signature",
    "exp"
  ]
}
```

负向验证：

```text
wrong_audience_rejected=True
```

`id_token`、`access_token`、`refresh_token` 未写入仓库文档，临时 token 文件已清理。

## Team Cloud 实施约束

1. JWT 验证必须从 OIDC discovery 获取 `issuer` 和 `jwks_uri`，并缓存 JWKS，支持 key rotation。
2. 默认必须校验 `iss`、`aud`、`exp`、`nbf`、`iat`、`sub` 和签名算法 allowlist。
3. `aud` 必须匹配 Team API / Team Web application client id，不能接受任意 Casdoor app token。
4. `sub` 只作为外部身份主键，必须映射到内部 `user_id/member_id` 后才能进入权限判断。
5. 禁用用户、成员暂停、组织禁用必须在 Team Cloud member status 层 fail closed，不能只依赖 token 未过期。
6. 本地开发可使用 HTTP issuer；Beta/GA 私有化默认必须使用 HTTPS issuer。
7. password grant 仅允许作为受控 smoke harness；Team Web 生产路径使用 authorization code + PKCE。

## P1 影响

- `P1-03` compose 需要 Casdoor seed job 创建 Team Web 和 Team API application，写入 redirect URI、client id、client secret。
- `P1-05` Casdoor OIDC 接入需要实现 discovery fetch、JWKS cache、token validation 和 key rotation。
- `P1-06` JWT middleware 需要覆盖 issuer/audience/signature/exp/nbf/member status 负测。
- `P1-19` 平台基础测试需要复用本步骤的正向验证和 wrong-audience 负向验证。

## 清理结果

临时容器 `hermes-p0-06-casdoor` 和 `/tmp/hermes-p0-06-*` token/数据库文件已删除。仓库未保存任何敏感 token。
