# P1-16 Web 登录壳工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-16。
- 将 P1-03 的静态 web shell 升级为最小可用 Web 登录壳：Casdoor login callback、session、organization switcher。

## 执行记录

- 2026-05-22：启动 P1-16，读取现有 `deploy/team-cloud/web-shell/index.html`、P1-05 OIDC 文档和 P1-16 工作包要求。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_web_login_shell.py`，覆盖 OIDC authorize/callback、sessionStorage、organization switcher、登录/登出/刷新和错误状态控件。
- 2026-05-22：红灯确认后替换 `deploy/team-cloud/web-shell/index.html`，实现登录 view、app view、OIDC authorize/callback、`sessionStorage.hermesTeamSession`、组织切换器、刷新、登出、错误和 empty state。
- 2026-05-22：新增 `teamDoc/GADoc/P1-16-web-login-shell.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_web_login_shell.py`
  - 结果：`2 tests failed, 0 passed`。
  - 失败点：静态占位页缺少 `/auth/oidc/authorize`、`/auth/oidc/callback`、`sessionStorage`、`hermesTeamSession`、`organization-switcher`、`/api/organizations`、`data-view` 和操作控件。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_web_login_shell.py`
  - 结果：`2 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_web_login_shell.py`
  - 结果：`82 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
