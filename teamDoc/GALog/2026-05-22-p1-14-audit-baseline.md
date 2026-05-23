# P1-14 Audit 基础能力工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-14。
- 实现 audit events 服务层、请求审计 middleware 和查询 API。

## 执行记录

- 2026-05-22：启动 P1-14，基于 PostgreSQL `audit_events` schema 和 P1 管理/API 中间件边界设计最小审计能力。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_audit_baseline.py`，覆盖 audit 记录/过滤、HTTP request 审计和查询 API。
- 2026-05-22：红灯确认后新增 `team_cloud/audit.py`，实现 `InMemoryAuditLog.record()` 和 `query()`。
- 2026-05-22：更新 `team_cloud/api.py`，在提供 `audit_log` 时挂载 HTTP request 审计 middleware 和 `/api/audit/events` 查询 API。
- 2026-05-22：新增 `teamDoc/GADoc/P1-14-audit-baseline.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_audit_baseline.py`
  - 结果：`3 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.audit'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_audit_baseline.py`
  - 结果：`3 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/audit.py team_cloud/api.py tests/team_cloud/test_audit_baseline.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_audit_baseline.py`
  - 结果：`76 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
