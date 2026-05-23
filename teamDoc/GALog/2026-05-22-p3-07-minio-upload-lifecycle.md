# P3-07 MinIO upload/lifecycle 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-07。
- 将 P3-06 `BackupExportResult` 上传到 personal backup object store。
- 写入 object manifest 兼容记录和 backup job 兼容记录。
- 提供 owner-scoped signed URL。
- 支持按 member policy 的 `retention_count` 清理旧备份。
- 不在本步骤实现真实 MinIO SDK、PostgreSQL repository、调度 worker 或恢复流程。

## 执行记录

- 2026-05-22：在 P3-06 完成并通过 foundation smoke 后启动 P3-07。
- 2026-05-22：读取 P0-09/P1-15 MinIO manifest 规范、`object_manifests`
  与 `backup_jobs` schema、`ObjectManifestService` 和 P3-06 exporter，
  确认最小实现为 in-memory `PersonalBackupStorageService`。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_backup_storage.py`
  失败符合预期，2 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.backup.storage'`。
- 绿灯：新增 `team_cloud.backup.storage.PersonalBackupStorageService`，
  并为 `ObjectManifestService` 补齐 active/deleted lifecycle 状态后，
  `scripts/run_tests.sh tests/team_cloud/test_backup_storage.py` 通过，
  2 passed / 0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，16 passed / 0 failed。
- `venv/bin/ruff check team_cloud/backup team_cloud/storage/minio.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/backup/exporter.py team_cloud/backup/storage.py team_cloud/storage/minio.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，53 files / 196 tests
  passed / 0 failed。
