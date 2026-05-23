# P3-06 加密 JSONL exporter 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-06。
- 从 personal memory 生成 `memories.jsonl`、`memory_events.jsonl`、
  `manifest.json` 和 `README.md` 的备份包。
- 生成加密后的 `backup.zip.enc` bytes，计算 encrypted payload checksum。
- 支持 `org_managed` envelope encryption 和 `user_passphrase` 模式。
- 不在本步骤上传 MinIO、不写 `object_manifests`、不实现 restore preview。

## 执行记录

- 2026-05-22：在 P3-05 完成并通过 foundation smoke 后启动 P3-06。
- 2026-05-22：读取 `teamDoc/15-minio-personal-backup.md`、
  `P0-09 MinIO key/manifest`、`InMemoryMemoryService` 和
  `ObjectManifestService`，确认本步骤输出为本地加密备份包和 manifest
  contract，MinIO 上传由 P3-07 承接。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_backup_exporter.py`
  失败符合预期，3 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.backup.exporter'`。
- 绿灯：新增 `team_cloud.backup.exporter.PersonalMemoryBackupExporter`、
  `BackupEncryptionKey`、`BackupExportResult` 和 `decrypt_backup_package()`
  后，`scripts/run_tests.sh tests/team_cloud/test_backup_exporter.py`
  通过，3 passed / 0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，10 passed / 0 failed。
- `venv/bin/ruff check team_cloud/backup tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/backup/exporter.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，52 files / 194 tests
  passed / 0 failed。
