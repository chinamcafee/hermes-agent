# P1-11 Relationship outbox 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-11。
- 实现 SpiceDB relationship outbox 的幂等 enqueue、pending/failed 处理、重试、dead letter 和资源 fail-closed 判断。
- 当前阶段使用内存 repository 固定行为契约，后续接入 PostgreSQL `spicedb_outbox` 表。

## 执行记录

- 2026-05-22：启动 P1-11，读取 auth permission design 的 outbox 一致性章节、target architecture 和 PostgreSQL `spicedb_outbox` schema。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_relationship_outbox.py`，覆盖幂等入队、relationship 序列化、worker 成功应用、失败重试、dead letter 和 fail-closed 判断。
- 2026-05-22：红灯确认后新增 `team_cloud/authz/outbox.py`，实现 `RelationshipOutboxItem`、`InMemoryRelationshipOutboxRepository`、`RelationshipOutboxService` 和 `RelationshipOutboxWorker`。
- 2026-05-22：更新 `team_cloud/authz/__init__.py` 导出 outbox primitives。
- 2026-05-22：新增 `teamDoc/GADoc/P1-11-relationship-outbox.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_relationship_outbox.py`
  - 结果：`4 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.authz.outbox'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_relationship_outbox.py`
  - 结果：`4 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/authz tests/team_cloud/test_relationship_outbox.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py`
  - 结果：`64 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
