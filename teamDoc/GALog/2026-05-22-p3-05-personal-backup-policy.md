# P3-05 Personal backup policy 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-05。
- 实现个人记忆备份 policy 的 cadence、retention、include options、
  encryption mode 和通知偏好。
- 提供 API 契约，供 Web Personal Memory 页面和后续 backup worker 使用。
- 不在本步骤实现 exporter、MinIO upload、restore preview 或 restore execute。

## 执行记录

- 2026-05-22：在 P3-04 完成并通过 foundation smoke 后启动 P3-05。
- 2026-05-22：读取 `backup_policies` schema、P0-09 MinIO 模型、
  `teamDoc/15-minio-personal-backup.md`、memory CRUD service 和 API
  注入模式，确认最小实现为 in-memory backup policy service + API。
- 2026-05-22：新增 `team_cloud.backup.policy.BackupPolicyService`，
  支持 `daily/weekly/monthly`、retention、include options、
  `org_managed/user_passphrase` 和通知渠道偏好。
- 2026-05-22：在 `team_cloud.api.create_app()` 接入
  `/v1/me/memory-backup-policy` GET/PUT，供 Web Personal Memory 页面和
  后续 backup worker 共享同一 policy contract。
- 2026-05-22：新增 `teamDoc/GADoc/P3-05-personal-backup-policy.md`，
  并将 `tests/team_cloud/test_backup_policy.py` 登记进 foundation smoke。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_backup_policy.py`
  失败符合预期，4 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.backup'`。
- 绿灯：新增 backup policy service 和 API 路由后，`scripts/run_tests.sh
  tests/team_cloud/test_backup_policy.py` 通过，4 passed / 0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，7 passed / 0 failed。
- `venv/bin/ruff check team_cloud/backup/policy.py team_cloud/api.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/api.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，51 files / 191 tests
  passed / 0 failed。
