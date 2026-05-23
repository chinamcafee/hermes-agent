# P3-18 Backup/restore tests 工作日志

日期：2026-05-22
状态：Done

## 目标

- 按 `GAStep` 顺序推进 P3-18。
- 增加 personal backup 从 export、upload、download URL、restore preview 到 restore execute 的端到端测试。
- 覆盖 checksum mismatch 阻止恢复和不产生 restore staging/job 的安全断言。
- 将备份恢复演练纳入 foundation smoke。

## 执行记录

- 2026-05-22：P3-17 完成并通过 foundation smoke 后启动 P3-18。
- 2026-05-22：读取 P3-06/P3-07/P3-08/P3-09 相关 exporter、storage、restore service 和既有测试，确认本步骤以自动化演练测试为主，避免重复改写备份恢复核心实现。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py`
  失败符合预期，2 个测试全部失败；失败原因为
  `team_cloud.backup.drill` 模块不存在，尚未提供端到端 backup/restore
  演练 helper。
- 绿灯：新增 `team_cloud/backup/drill.py` 并导出
  `PersonalBackupRestoreDrill` 后重跑
  `scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py`，
  1 个测试文件、2 个测试通过、0 失败。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py
  tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py
  tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py
  tests/team_cloud/test_platform_foundation_suite.py`：6 个测试文件、15 个测试通过、0 失败。
- `venv/bin/ruff check team_cloud/backup/drill.py team_cloud/backup/__init__.py
  tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py
  tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py
  tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m py_compile team_cloud/backup/drill.py team_cloud/backup/__init__.py
  tests/team_cloud/test_backup_restore_drill.py tests/team_cloud/test_backup_exporter.py
  tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py
  tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py`：通过。
- `venv/bin/python -m json.tool
  teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json`：通过。
- `scripts/team-cloud-foundation-smoke.sh`：64 个测试文件、224 个测试通过、0 失败。
- `git diff --check -- ...P3-18 touched files...`：通过。

## 完成记录

- 2026-05-22：P3-18 Backup/restore tests 已完成，foundation smoke 纳入
  `backup_restore_drill` domain；P3-19 AuthZ chaos tests 待启动。
- 2026-05-22：同步校正 P3 总人周为 56.5，避免 P3-18 后 P3 显示 100%
  但 P3-19 到 P3-22 仍未完成。
