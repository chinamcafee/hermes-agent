# P3-09 Restore execute

日期：2026-05-22
状态：Implemented
前置：`P3-08 Restore preview`

## 目标

本步骤执行 P3-08 生成的 restore preview，把用户选择的恢复模式落到 personal memory store。实现覆盖 `merge`、`overwrite`、`archive_current_then_restore` 三种模式，并为新增或更新的 memory 记录 embedding rebuild 请求。异步 embedding worker 编排、通知、Web UI 和持久化 PostgreSQL repository 后续继续接入。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/restore.py` | 新增 `RestoreExecutionService` 和 restore job contract。 |
| `tests/team_cloud/test_restore_execute.py` | 覆盖 merge、overwrite、archive-current-then-restore。 |
| `teamDoc/GALog/2026-05-22-p3-09-restore-execute.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `restore_execute` domain。 |

## Execution Contract

`RestoreExecutionService.execute_preview(preview, mode, actor_member_id)` 要求 `preview.status=previewed`。

| Preview action | `merge` | `overwrite` | `archive_current_then_restore` |
| --- | --- | --- | --- |
| `skip` | 跳过 | 跳过 | 跳过 |
| `create` | 创建 active personal memory | 创建 active personal memory | 创建 active personal memory |
| `conflict` | 保留为 unresolved conflict | 更新 current memory | archive current 后创建 restored memory |

执行结果写 in-memory restore job：

- `status=succeeded`：无未处理冲突。
- `status=blocked`：仍有 unresolved conflict。
- `summary.created/updated/archived/skipped/conflicts`。
- `restored_memory_ids`。
- `embedding_rebuild_requested`。

## Embedding Rebuild

本步骤不直接调用 embedding worker，而是把新增或更新的 memory id 写入 `embedding_rebuild_queue` 和 job 的 `embedding_rebuild_requested` 字段。P4/P5 或后续 runtime wiring 可将该队列接入现有 P2 embedding worker。

## 非目标

- 不实现 restore API/Web UI。
- 不实现 PostgreSQL `restore_jobs` repository。
- 不直接运行 embedding worker。
- 不发送通知。
- 不实现跨成员或团队记忆恢复。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_restore_execute.py
scripts/run_tests.sh tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/restore.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_restore_execute.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
