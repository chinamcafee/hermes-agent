# P1-15 MinIO client 和 manifest 工作日志

## 目标

- 按 `GAStep` 顺序推进 P1-15。
- 实现 MinIO bucket bootstrap、对象上传、manifest 生成和短期 signed URL 的最小服务层。
- 当前阶段不引入 MinIO SDK，先固定可替换 object store 协议和 manifest 行为。

## 执行记录

- 2026-05-22：启动 P1-15，读取 P0-09 MinIO key/manifest 规范、manifest JSON Schema 和 `object_manifests` schema。
- 2026-05-22：按 TDD 新增 `tests/team_cloud/test_minio_manifest.py`，覆盖 bucket bootstrap、personal backup manifest、signed URL 和必填字段校验。
- 2026-05-22：红灯确认后新增 `team_cloud/storage/minio.py` 和 `team_cloud/storage/__init__.py`。
- 2026-05-22：实现 `InMemoryObjectStore` 和 `ObjectManifestService`，覆盖 bucket bootstrap、put object、manifest 生成和短期 presigned URL。
- 2026-05-22：新增 `teamDoc/GADoc/P1-15-minio-manifest.md`。

## 验证记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py`
  - 结果：`4 tests failed`。
  - 失败点：`ModuleNotFoundError: No module named 'team_cloud.storage'`。
- 绿灯：`scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py`
  - 结果：`4 tests passed, 0 failed`。
- Ruff 聚焦：`venv/bin/ruff check team_cloud/storage tests/team_cloud/test_minio_manifest.py`
  - 结果：`All checks passed!`。
- 回归：`scripts/run_tests.sh tests/test_project_metadata.py tests/team_cloud/test_config_secret_management.py tests/team_cloud/test_skeleton.py tests/team_cloud/test_local_compose_stack.py tests/team_cloud/test_postgres_migrations.py tests/team_cloud/test_casdoor_oidc.py tests/team_cloud/test_jwt_middleware.py tests/team_cloud/test_casdoor_sync_worker.py tests/team_cloud/test_pat_service_accounts.py tests/team_cloud/test_spicedb_client.py tests/team_cloud/test_spicedb_schema_ci.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_minio_manifest.py`
  - 结果：`80 tests passed, 0 failed`。
- Ruff 回归：`venv/bin/ruff check team_cloud tests/team_cloud`
  - 结果：`All checks passed!`。
- 语法检查：`venv/bin/python -m compileall -q team_cloud`
  - 结果：退出码 0。
