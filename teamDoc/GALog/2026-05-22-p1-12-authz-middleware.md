# P1-12 AuthZ middleware 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-12。
- 实现 Team API permission gate、SpiceDB check fail closed、relationship outbox pending fail closed 和 permission cache key。

## 执行记录

- 2026-05-22：启动 P1-12，基于 P1-09 AuthzClient 和 P1-11 Relationship outbox 行为设计 FastAPI middleware 边界。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_authz_middleware.py`，覆盖 allow、deny、SpiceDB error、outbox pending 和 unmatched route skip。
- 2026-05-22：红灯确认后新增 `team_cloud/authz/middleware.py`，实现 route permission rule、AuthZ middleware 和 permission cache key。
- 2026-05-22：更新 `team_cloud/authz/__init__.py` 导出 middleware primitives。
- 2026-05-22：新增 `teamDoc/GADoc/P1-12-authz-middleware.md`。

## 调试记录

- 首次实现后新增测试返回 `401`：
  - 根因：FastAPI middleware 执行顺序导致测试中设置 principal 的 middleware 没有在 AuthZ middleware 前生效。
  - 修复：测试改用 `subject_resolver` 注入，隔离 P1-12 关注的权限 gate 行为；生产默认 resolver 仍支持 `request.state.principal` 和 `request.state.token_principal`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_authz_middleware.py`
  - 结果：`5 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.authz.middleware'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_authz_middleware.py`
  - 结果：`5 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/authz tests/team_cloud/test_authz_middleware.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py`
  - 结果：`69 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
