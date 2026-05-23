# P3-08 Restore preview

日期：2026-05-22
状态：Implemented
前置：`P3-06 加密 JSONL exporter`、`P3-07 MinIO upload/lifecycle`

## 目标

本步骤实现个人备份恢复的预览阶段：校验加密包 checksum，解密备份 zip，读取 `memories.jsonl` staging 数据，并与当前 personal memory 做只读对比，输出 create、skip、conflict 计数和逐项 diff。恢复执行、merge/overwrite/archive-old 策略落地和 embedding rebuild 留给 P3-09。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/restore.py` | `RestorePreviewService`，生成只读 restore preview。 |
| `tests/team_cloud/test_restore_preview.py` | 覆盖 create/skip/conflict 预览和 checksum mismatch 阻断。 |
| `teamDoc/GALog/2026-05-22-p3-08-restore-preview.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `restore_preview` domain。 |

## Preview Contract

`RestorePreviewService.preview_personal_restore()` 输入：

- `org_id`
- `member_id`
- encrypted backup bytes
- P3-06/P3-07 manifest
- org-managed key resolver 或 user passphrase

流程：

1. 校验 manifest owner 与请求的 `org_id/member_id` 一致。
2. 调用 `decrypt_backup_package()`，先校验 encrypted checksum，再解密，再校验 plaintext checksum。
3. 读取 zip 中的 `memories.jsonl`。
4. 与当前 `scope=personal` 且 `subject_member_id=<member_id>` 的 memory 对比。
5. 返回 `status=previewed` 的 preview，不修改 `memory_items`。

## Conflict Rules

| 场景 | Preview action | Reason | 默认策略 |
| --- | --- | --- | --- |
| 当前 active memory checksum 相同 | `skip` | `checksum_match` | 无需恢复 |
| 当前 memory 已 deleted，但 normalized content 相同 | `conflict` | `current_deleted` | `ask_user` |
| normalized content 相同且当前版本更新或相同 | `skip` | `keep_newer` | 保留当前 |
| normalized content 相同但备份版本更新 | `conflict` | `backup_newer` | `review` |
| 当前不存在匹配内容 | `create` | `new_memory` | P3-09 创建 |

`summary` 固定包含 `total/create/skip/conflict/overwrite`，其中 `overwrite` 在 P3-08 仅作为预览出口字段保留，实际覆盖执行由 P3-09 决定。

## 非目标

- 不写 `restore_jobs` 持久化 repository。
- 不执行 merge、overwrite 或 archive-current-then-restore。
- 不重建 embedding。
- 不发送通知。
- 不实现 Web restore UI。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_restore_preview.py
scripts/run_tests.sh tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/exporter.py team_cloud/backup/storage.py team_cloud/backup/restore.py tests/team_cloud/test_backup_exporter.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_restore_preview.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
