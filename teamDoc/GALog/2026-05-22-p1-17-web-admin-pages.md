# P1-17 Web 成员/团队/角色页工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-17。
- 在 P1-16 登录壳基础上增加 members、teams、roles 三个最小管理页。
- 支持列表、创建、禁用、角色展示、empty/error/loading 状态。

## 执行记录

- 2026-05-22：启动 P1-17，读取 P1-13 管理 API 文档、P1-16 Web 登录壳和工作包要求。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_web_admin_pages.py`，覆盖成员列表 API、Web teams/members/roles 面板、组织作用域 API wiring 和错误态。
- 2026-05-22：红灯确认后在 `team_cloud/admin/organizations.py` 和 `team_cloud/api.py` 补齐成员列表 API。
- 2026-05-22：扩展 `deploy/team-cloud/web-shell/index.html`，新增 teams/members/roles tabs、团队创建、成员邀请、成员禁用、角色矩阵、面板级错误态和 empty state。
- 2026-05-22：新增 `teamDoc/GADoc/P1-17-web-admin-pages.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_web_admin_pages.py`
  - 结果：`3 tests failed, 0 passed`。
  - 失败点：成员列表 API 返回 404；Web 壳缺少 `data-admin-tab`、teams/members/roles panel、组织作用域 API wiring 和错误态。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_web_admin_pages.py`
  - 结果：`3 tests passed, 0 failed`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_web_login_shell.py tests/team_cloud/test_web_admin_pages.py`
  - 结果：`85 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
