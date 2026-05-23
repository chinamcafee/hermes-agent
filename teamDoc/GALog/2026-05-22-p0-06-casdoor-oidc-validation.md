# GALog 2026-05-22 P0-06 Casdoor OIDC 验证

## 工作粒度

- 工作包：`P0-06 Casdoor OIDC 验证`
- 类型：协议烟测 / 身份认证验证
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/13-casdoor-spicedb-integration.md`
- `teamDoc/GADoc/P0-04-component-version-license-freeze.md`
- `teamDoc/GADoc/P0-05-local-topology-design.md`

## 产出

- 新增：`teamDoc/GADoc/P0-06-casdoor-oidc-validation.md`

## 执行记录

1. 确认本机 Docker 可用：`Docker version 29.1.2`，`Docker Compose version v2.40.3-desktop.1`。
2. 直接运行 `casbin/casdoor:3.60.1` 失败，原因是默认 app.conf 连接本机 MySQL `localhost:3306`。
3. 改用同版本 `casbin/casdoor-all-in-one:3.60.1` 启动临时容器，OIDC discovery 成功返回 issuer/token/JWKS endpoint。
4. 为自动化烟测在临时 SQLite 数据库中给内置 application 开启 password grant；该偏差不进入 GA 登录路径。
5. 调用 token endpoint 获得 `id_token`，未将 token 写入仓库。
6. 使用 `PyJWT` + JWKS 验证 `issuer`、`audience`、`signature`、`exp`，并执行 wrong-audience 负测。
7. 删除临时容器和 `/tmp/hermes-p0-06-*` 文件。

## 验证证据

正向验证摘要：

```json
{
  "verified": true,
  "algorithm": "RS256",
  "kid": "cert-built-in",
  "issuer": "http://localhost:18000",
  "audience": [
    "5d17b05caf9b4295b1c9"
  ],
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

负向验证摘要：

```text
wrong_audience_rejected=True
```

## 决策摘要

1. Casdoor `3.60.1` OIDC discovery、JWKS 和 `id_token` RS256 验签可用于 Team Cloud。
2. Team Cloud JWT middleware 必须严格校验 issuer、audience、signature、exp/nbf/iat/sub。
3. P1 compose 不能照搬 all-in-one；all-in-one 仅作为 P0-06 烟测工具。
4. password grant 仅用于自动化 smoke harness；生产登录必须 authorization code + PKCE。

## 验证计划

- 检查 P0-06 文档包含 discovery、id_token 验证结果、issuer/audience/signature/exp、负向验证和清理说明。
- 检查没有把 token 值写入仓库文档。
- 验证后更新 `progress-tracker.md` 中 `P0-06` 为 `Done`。

## 后续

- 进入 `P0-07 SpiceDB schema v0`。
