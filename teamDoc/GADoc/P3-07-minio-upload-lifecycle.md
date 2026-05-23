# P3-07 MinIO upload/lifecycle

日期：2026-05-22
状态：Implemented
前置：`P3-06 加密 JSONL exporter`、`P1-15 MinIO client 和 manifest`

## 目标

本步骤把 P3-06 的加密备份包接入对象存储 contract：上传 `BackupExportResult.encrypted_bytes`，生成 personal backup object manifest，写 backup job 兼容记录，提供 owner-scoped signed URL，并按 `retention_count` 删除旧备份。实现仍使用 P1-15 的 in-memory object store，真实 MinIO SDK、PostgreSQL repository、调度 worker 和恢复流程留给后续阶段。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/storage.py` | `PersonalBackupStorageService`，负责 upload、signed URL、retention cleanup。 |
| `team_cloud/storage/minio.py` | `ObjectManifestService` 增加 `status/deleted_at` 和 `mark_deleted()`。 |
| `tests/team_cloud/test_backup_storage.py` | 覆盖 upload/job、owner URL、TTL、retention cleanup。 |
| `teamDoc/GALog/2026-05-22-p3-07-minio-upload-lifecycle.md` | TDD 红绿记录和回归证据。 |

## Upload Contract

`PersonalBackupStorageService.upload_export()` 输入 P3-06 `BackupExportResult`：

1. 校验 encrypted bytes 的 SHA-256 与 export manifest 一致。
2. 调用 `ObjectManifestService.upload_object(object_type="personal_backup")`。
3. 生成 P0-09 key pattern：
   `org/{org_id}/member/{member_id}/personal-memory/{yyyy}/{mm}/{backup_id}/backup.zip.enc`。
4. manifest 记录 `bucket/object_key/checksum/encryption/retention/status`。
5. 写 in-memory `backup_jobs` 兼容记录，状态为 `succeeded`。

## Download URL

`signed_download_url()` 只对同一 `org_id + member_id + backup_id` 的 active personal backup 返回 URL。owner 不匹配返回 `backup_owner_mismatch`，不存在或已删除返回 `backup_not_found`。TTL 继续沿用 P1-15 的 `<= 5 分钟` 限制。

## Retention Cleanup

`cleanup_retention(org_id, member_id, retention_count)` 只扫描该成员 active personal backup，按 `created_at` 倒序保留最近 N 份；旧对象通过 `ObjectManifestService.mark_deleted()` 删除 object store bytes，并把 manifest 标记为 `deleted`、写 `deleted_at`。其他成员和其他 object type 不受影响。

## 非目标

- 不引入真实 MinIO SDK。
- 不实现 PostgreSQL `object_manifests` / `backup_jobs` repository。
- 不执行 due policy scheduler。
- 不实现 restore preview/execute。
- 不实现通知发送或审计高级页面。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_backup_storage.py
scripts/run_tests.sh tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup team_cloud/storage/minio.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/backup/exporter.py team_cloud/backup/storage.py team_cloud/storage/minio.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_minio_manifest.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
