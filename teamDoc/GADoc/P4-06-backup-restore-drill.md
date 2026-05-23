# P4-06 Backup/restore drill

日期：2026-05-23
状态：Implemented
前置：`P3 数据治理与权限硬化`

## 目标

本步骤把 P3 的 personal memory backup/restore drill 扩展为 P4 Beta 平台级恢复演练 evidence contract，覆盖 PostgreSQL PITR、SpiceDB relationship snapshot、MinIO bucket restore、Casdoor config restore、personal memory restore 和 org export rehydrate。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/drill.py` | 新增 `PlatformBackupRestoreDrill`，生成平台级恢复演练报告。 |
| `scripts/team-cloud-backup-restore-drill.py` | 本地 deterministic drill runner，输出 JSON evidence artifact。 |
| `teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json` | P4-06 平台恢复演练证据。 |
| `tests/team_cloud/test_platform_backup_restore_drill.py` | P4-06 contract 测试。 |

## 覆盖域

| Domain | 恢复动作 | 验证 |
| --- | --- | --- |
| PostgreSQL PITR | restore base backup and replay WAL | migration、核心表、memory rows 查询 |
| SpiceDB relationship snapshot | load snapshot and replay relationship outbox | schema hash、permission fixtures、outbox replay idempotency |
| MinIO bucket restore | restore buckets and validate manifests | lifecycle、checksum、signed download URL |
| Casdoor config restore | import org/app/provider config | OIDC discovery、JWKS、disabled member status |
| Personal memory restore | encrypted backup download、preview、merge restore | restore job succeeded、embedding rebuild requested |
| Org export rehydrate | staging import and relationship replay | metadata、cloud sessions、relationships |

## 非目标

- 不在单测中启动真实 PostgreSQL、SpiceDB、MinIO 或 Casdoor。
- 不替代试点环境的人工变更冻结和 live restore 窗口。
- 不写入生产数据；当前 runner 使用 in-memory memory service 生成 deterministic evidence。

## 运行

```bash
scripts/team-cloud-backup-restore-drill.py --output teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_platform_backup_restore_drill.py
scripts/run_tests.sh tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup/drill.py scripts/team-cloud-backup-restore-drill.py tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/drill.py scripts/team-cloud-backup-restore-drill.py tests/team_cloud/test_platform_backup_restore_drill.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/drills/team-cloud-backup-restore-drill-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
