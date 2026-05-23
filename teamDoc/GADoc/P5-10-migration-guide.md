# P5-10 Migration guide

日期：2026-05-23
状态：Implemented
前置：`P2-22 SessionDB 迁移工具`

## 目标

本步骤固定 Team Cloud GA migration guide contract，覆盖 `SessionDB` 导入、`legacy memory provider` 数据迁移、`identity_map`、`dry_run` validation、scope mapping 和 rollback。迁移默认 fail closed：未映射身份只进入报告，不自动创建成员或绑定外部身份。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/migration_guide.py` | `build_migration_guide_package()` 生成 migration guide JSON contract。 |
| `scripts/team-cloud-migration-guide.py` | 写出 migration guide JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-migration-guide-v0.json` | P5-10 migration guide artifact。 |
| `tests/team_cloud/test_migration_guide.py` | P5-10 contract 测试。 |

## Migration paths

| ID | Source | Target / Command |
| --- | --- | --- |
| `sessiondb_import` | Hermes SessionDB | `scripts/team-cloud-import-sessiondb.py` |
| `legacy_memory_provider_export` | legacy memory provider | export_jsonl -> Team Cloud Memory API |
| `memory_scope_mapping` | legacy memory records | target scopes：`personal`、`team_shared` |
| `dry_run_validation` | migration report | `scripts/team-cloud-import-sessiondb.py --dry-run` |
| `rollback_snapshot` | pre-cutover snapshot | `keep_sessiondb_readonly_snapshot`、`restore_postgres_snapshot` |

## SessionDB

迁移命令必须显式提供：

- `--db`
- `--org-id`
- `--team-id`
- `--project-id`
- `--identity-map`
- `--dry-run`

`identity_map` 将本地 `user_id` 映射为 Team Cloud `member_id`。未映射身份输出 `unmapped_sessions`，不写入 cloud session。

## legacy memory provider

旧 memory provider 迁移必须先导出为 `export_jsonl`，每行至少包含：

- `content`
- `scope`
- `member_id`
- `team_id`
- `metadata`

映射规则：

- member-owned facts -> `personal`
- organization-approved shared facts -> `team_shared`

## validation_checks

- `unmapped_identity_report`
- `duplicate_conflict_review`
- `pii_secret_scan`
- `isolation_smoke`
- `backup_before_cutover`

## rollback_steps

1. `freeze_source_writes`
2. `keep_sessiondb_readonly_snapshot`
3. `restore_postgres_snapshot`
4. `restore_minio_backup_objects`
5. `rerun_foundation_smoke`

## 运行

```bash
scripts/team-cloud-migration-guide.py --output teamDoc/GADoc/artifacts/release/team-cloud-migration-guide-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_migration_guide.py
scripts/run_tests.sh tests/team_cloud/test_migration_guide.py tests/team_cloud/test_sessiondb_import.py tests/team_cloud/test_team_memory_provider.py tests/team_cloud/test_memory_duplicate_conflict_detector.py tests/team_cloud/test_memory_pii_secret_detector.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/migration_guide.py scripts/team-cloud-migration-guide.py tests/team_cloud/test_migration_guide.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/migration_guide.py scripts/team-cloud-migration-guide.py tests/team_cloud/test_migration_guide.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-migration-guide-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
