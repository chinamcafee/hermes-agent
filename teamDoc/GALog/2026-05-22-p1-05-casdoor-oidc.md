# P1-05 Casdoor OIDC 接入

## 工作目标

- 按 `teamDoc/GAStep/01-work-package-register.md` 的 P1-05 执行。
- 主要产出：authorize/callback/token/JWKS 校验。
- 遵循 P0-06：discovery 获取 issuer/JWKS，JWKS cache 支持 key rotation，校验 issuer/audience/signature/exp/nbf/iat/sub。
- 不实现 P1-06 JWT middleware 和 member status fail-closed。

## 2026-05-22 执行记录

### 1. 启动 P1-05

- 前置确认：P1-01 到 P1-04 已在 `progress-tracker.md` 标记 `Done`。
- 规格输入：`P0-06 Casdoor OIDC 验证`、`ADR-0001`、`teamDoc/13-casdoor-spicedb-integration.md`。
- 当前边界：实现 Team Cloud 侧 OIDC client 和最小 API routes；不保存 session，不做 membership 状态校验，不把 Casdoor roles/groups 当最终授权。

### 2. 红灯测试设计

- 新增 `tests/team_cloud/test_casdoor_oidc.py`，覆盖：
  - authorize URL 使用 authorization code + state + nonce + PKCE。
  - code exchange POST 到 discovery token endpoint。
  - id_token 验证 issuer/audience/signature/exp/nbf/iat/sub。
  - wrong audience 被拒绝。
  - JWKS unknown `kid` 会刷新 cache，支持 key rotation。
  - API 暴露 `/auth/oidc/authorize` 和 `/auth/oidc/callback` 最小路由。

### 3. 最小实现

- 新增 `team_cloud/auth/` package。
- 新增 `team_cloud/auth/oidc.py`：
  - `CasdoorOIDCClient`
  - `OIDCDiscovery`
  - `TokenSet`
  - `OIDCVerificationError`
  - discovery fetch/cache
  - authorize URL builder
  - authorization code token exchange
  - JWKS cache + unknown `kid` refresh
  - `RS256` id_token 验证
- 更新 `team_cloud/api.py`：
  - `create_app(..., oidc_client=...)` 支持测试注入。
  - `GET /auth/oidc/authorize` 返回 authorization URL、state、nonce。
  - `GET /auth/oidc/callback` 完成 code exchange 和 id_token verify，只返回非敏感 subject/email/name/state。
- 新增 `teamDoc/GADoc/P1-05-casdoor-oidc.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_casdoor_oidc.py`
  - 结果：`6 tests failed`。
  - 失败点：缺少 `team_cloud.auth` package、`CasdoorOIDCClient`、`OIDCVerificationError` 和 API OIDC routes。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_casdoor_oidc.py`
  - 结果：`6 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py`
  - 结果：`39 tests passed, 0 failed`。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
