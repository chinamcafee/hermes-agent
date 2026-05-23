# P1-13 组织/团队/成员 API 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-13。
- 实现组织、团队、成员的最小管理 API：组织创建/list、团队创建/list、成员邀请、成员禁用。
- 成员禁用时同步写 relationship delete outbox intent。

## 执行记录

- 2026-05-22：启动 P1-13，沿用 P1-11 relationship outbox 和 P1-12 AuthZ middleware 的服务边界。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_admin_org_api.py`，覆盖组织/团队创建和列表、成员邀请、成员禁用、outbox 写入和 404 错误态。
- 2026-05-22：红灯确认后新增 `team_cloud/admin/organizations.py` 和 `team_cloud/admin/__init__.py`。
- 2026-05-22：更新 `team_cloud/api.py`，在提供 `organization_service` 时挂载组织/团队/成员管理 API。
- 2026-05-22：新增 `teamDoc/GADoc/P1-13-org-team-member-api.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_admin_org_api.py`
  - 结果：`4 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.admin'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_admin_org_api.py`
  - 结果：`4 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/admin team_cloud/api.py tests/team_cloud/test_admin_org_api.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_admin_org_api.py`
  - 结果：`73 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
