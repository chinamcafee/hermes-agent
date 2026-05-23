# P3-08 Restore preview 工作日志

日期：2026-05-22
状态：In Progress

## 目标

- 按 `GAStep` 顺序推进 P3-08。
- 校验 encrypted backup checksum，解密备份包并读取 JSONL staging。
- 生成 restore preview，标出 create、skip、conflict。
- 覆盖 checksum duplicate、normalized_content 冲突和当前已删除冲突。
- 不在本步骤执行恢复写入；P3-09 负责 merge/overwrite/archive-old。

## 执行记录

- 2026-05-22：在 P3-07 完成并通过 foundation smoke 后启动 P3-08。
- 2026-05-22：读取恢复流程规划、冲突策略和 P3-06/P3-07 工件，确认本步骤只生成 preview，不改变 `memory_items`。

## TDD 记录

- 红灯：`scripts/run_tests.sh tests/team_cloud/test_restore_preview.py`
  失败符合预期，2 个测试全部失败；失败原因为
  `ModuleNotFoundError: No module named 'team_cloud.backup.restore'`。
- 绿灯：新增 `team_cloud.backup.restore.RestorePreviewService` 后，
  `scripts/run_tests.sh tests/team_cloud/test_restore_preview.py` 通过，
  2 passed / 0 failed。

## 回归验证

- `scripts/run_tests.sh tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，10 passed / 0 failed。
- `venv/bin/ruff check team_cloud/backup tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，All checks passed。
- `venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/exporter.py team_cloud/backup/storage.py team_cloud/backup/restore.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py`
  通过，无编译错误。
- `venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null`
  通过。
- `scripts/team-cloud-foundation-smoke.sh` 通过，54 files / 198 tests
  passed / 0 failed。
