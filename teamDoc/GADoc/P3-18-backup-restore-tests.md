# P3-18 Backup/restore tests

日期：2026-05-22
状态：Implemented
前置：`P3-06 加密 JSONL exporter`、`P3-07 MinIO upload/lifecycle`、`P3-08 Restore preview`、`P3-09 Restore execute`

## 目标

本步骤把 personal memory 备份恢复从分段单测提升为可重复演练 contract：自动串起 export、MinIO manifest/upload、signed download URL、restore preview 和 restore execute，并验证 checksum mismatch 在恢复预览前阻断，且不会生成 preview staging 或 restore job。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/drill.py` | `PersonalBackupRestoreDrill`，编排既有 exporter/storage/restore service。 |
| `team_cloud/backup/__init__.py` | 导出 drill helper。 |
| `tests/team_cloud/test_backup_restore_drill.py` | 覆盖成功恢复演练和 checksum mismatch 阻断。 |
| `teamDoc/GALog/2026-05-22-p3-18-backup-restore-tests.md` | TDD 红绿记录和回归证据。 |

## Drill Contract

`PersonalBackupRestoreDrill.run_single_member_restore()` 执行：

```text
1. 从 source memory service 导出指定 org/member 的 personal memory。
2. 生成加密 backup.zip.enc 和外部 manifest。
3. 上传到 in-memory MinIO object store 并写 object manifest。
4. 生成 <= 5 分钟 signed download URL。
5. 从 object store 读取加密对象 bytes。
6. 对 target memory service 生成 restore preview。
7. 使用 merge 模式执行 restore。
8. 返回 evidence：object manifest、backup job、preview、restore job、restored source ids。
```

`run_checksum_mismatch_guard()` 会篡改 manifest checksum，断言 `RestorePreviewService` 在解密/预览前返回 `checksum_mismatch`。该路径不创建 preview，也不会执行 restore job。

## 非目标

- 不替代 P4 的真实 MinIO/PostgreSQL/SpiceDB/Casdoor 备份恢复演练。
- 不新增外部存储依赖；当前使用 in-memory object store 固定 contract。
- 不改变 exporter/storage/restore 的核心实现。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py
scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup/drill.py team_cloud/backup/__init__.py tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/drill.py team_cloud/backup/__init__.py tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
