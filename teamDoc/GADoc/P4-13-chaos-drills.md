# P4-13 Chaos drills

日期：2026-05-23
状态：Implemented
前置：`P4-06 备份恢复演练`

## 目标

本步骤固定 P4 chaos drill matrix，覆盖 `spicedb_outage`、`minio_write_failure` 和 `postgres_readonly` 三类局部故障，并要求每个演练有 expected behavior、acceptance、recovery evidence 和 rollback command。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/chaos.py` | `build_chaos_drill_matrix()` 生成 chaos drill 矩阵。 |
| `scripts/team-cloud-chaos-drills.py` | 写出 chaos drill JSON artifact。 |
| `teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json` | P4-13 chaos artifact。 |
| `tests/team_cloud/test_chaos_drills.py` | P4-13 contract 测试。 |

## 运行

```bash
scripts/team-cloud-chaos-drills.py --output teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_chaos_drills.py
scripts/run_tests.sh tests/team_cloud/test_chaos_drills.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_notifications.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/chaos.py scripts/team-cloud-chaos-drills.py tests/team_cloud/test_chaos_drills.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/chaos.py scripts/team-cloud-chaos-drills.py tests/team_cloud/test_chaos_drills.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/chaos/team-cloud-chaos-drills-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
