# P1-06 JWT 中间件

## 工作目标

- 按 `teamDoc/GAStep/01-work-package-register.md` 的 P1-06 执行。
- 主要产出：issuer/audience/expiry/nonce/status 校验接入 Team API request path。
- 复用 P1-05 `CasdoorOIDCClient.verify_id_token()`。
- 对成员状态 fail closed：非 active 不能访问受保护 API。

## 2026-05-22 执行记录

### 1. 启动 P1-06

- 前置确认：P1-05 已在 `progress-tracker.md` 标记 `Done`。
- 规格输入：`P0-06 Casdoor OIDC 验证`、`teamDoc/13-casdoor-spicedb-integration.md`。
- 当前边界：实现 FastAPI JWT middleware 和 principal 注入；不实现真实 DB member resolver，不做 P1-07 Casdoor 同步 worker。

### 2. 红灯测试设计

- 新增 `tests/team_cloud/test_jwt_middleware.py`，覆盖：
  - public health/auth path 不需要 Bearer。
  - 受保护 API 无 Bearer 返回 401。
  - verifier 抛错返回 401。
  - member status 非 active 返回 403。
  - active member 可访问 `/api/whoami`。
  - 响应不泄露原始 token。

### 3. 最小实现

- 新增 `team_cloud/auth/middleware.py`：
  - `TeamPrincipal`
  - `install_jwt_middleware()`
  - public path allowlist
  - Bearer token extraction
  - invalid/missing token 401
  - non-active member 403
  - active principal 注入 `request.state.principal`
- 更新 `team_cloud/auth/__init__.py` 导出 middleware primitives。
- 更新 `team_cloud/api.py`：
  - `create_app(..., enable_jwt_middleware=True, member_status_resolver=...)`
  - `/api/whoami` 受保护端点。
- 新增 `teamDoc/GADoc/P1-06-jwt-middleware.md`。

### 4. 调试记录

- 首次实现后 `test_active_member_principal_reaches_api_without_token_leakage` 返回 `422`。
- 根因：`team_cloud/api.py` 使用 `from __future__ import annotations`，`whoami(request: Request)` 的注解被延迟为字符串；`Request` 只存在于 `create_app()` 局部作用域，FastAPI 无法识别 request injection。
- 修复：在 `create_app()` 中把 FastAPI `Request` 放入模块全局 `_FastAPIRequest`，并用该名称标注 `whoami()` 参数。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_jwt_middleware.py`
  - 结果：`5 tests failed`。
  - 失败点：`create_app()` 尚未支持 `enable_jwt_middleware`、`member_status_resolver` 和 `/api/whoami` 受保护路由。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_jwt_middleware.py`
  - 结果：`5 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py`
  - 结果：`44 tests passed, 0 failed`。
- Ruff：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
