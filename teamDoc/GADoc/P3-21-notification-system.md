# P3-21 通知系统

日期：2026-05-22
状态：Implemented
前置：`P3-05 Personal backup policy`、`P3-14 Break-glass`、`P2-08 Review Queue API`、`P3-20 数据治理文档`

## 目标

本步骤提供 Team Cloud 内置通知事件队列，用于 GA 数据治理链路里的三类必须提醒：personal backup failure、break-glass access 和 memory review backlog。当前实现使用 in-memory service 固定事件 contract，后续 P4/P5 可以替换为 PostgreSQL repository、email/webhook dispatcher 或 UI inbox，但业务触发点和 API 语义保持稳定。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/notifications.py` | `InMemoryNotificationService`，提供 create/list/ack、dedupe 和三个专用通知 helper。 |
| `team_cloud/backup/storage.py` | backup upload/checksum failure 记录 failed job 并触发 `backup_failure`。 |
| `team_cloud/break_glass.py` | 非 delayed break-glass access 触发 `break_glass_accessed`。 |
| `team_cloud/memory/review.py` | `notify_review_backlog()` 根据 pending review 阈值触发 `review_backlog`。 |
| `team_cloud/api.py` | `GET /api/notifications` 和 `POST /api/notifications/{id}/ack`。 |
| `tests/team_cloud/test_notifications.py` | 覆盖通知服务、三类触发点和 API。 |

## Event Contract

通知事件包含：

```text
id
org_id
type
severity
recipient_member_ids
channels
resource_type
resource_id
payload
status
created_at
acknowledged_by
acknowledged_at
dedupe_key
```

当前事件类型：

| type | severity | recipient | payload |
| --- | --- | --- | --- |
| `backup_failure` | `warning` | backup owner | `backup_id`、`policy_id`、`error` |
| `break_glass_accessed` | `critical` | target member | `request_id`、`requester_member_id` |
| `review_backlog` | `warning` | reviewer list | `pending_count`、`review_kind`、`oldest_created_at` |

## Integration Rules

- Backup failure：`PersonalBackupStorageService.upload_export()` 在 checksum mismatch 或 object upload error 时记录 failed job，并按 policy channels 触发通知；相同 backup/policy/error 使用 dedupe key 合并。
- Break-glass：`BreakGlassService.record_access()` 保留原有 `notifications` list 兼容旧 contract，同时写入 `InMemoryNotificationService`；`delayed_notification=true` 时不立即通知。
- Review backlog：`InMemoryMemoryReviewService.notify_review_backlog()` 只在 pending count 达到阈值时发通知，低于阈值返回 `None`。
- API：通知查询按 org、recipient、status、type 过滤；ack 需要 `actor_member_id` 并写 `acknowledged_at`。

## 非目标

- 不发送真实 email/webhook。
- 不新增前端 inbox；P3-22 Admin UX 收尾可补 empty/error/permission states。
- 不引入外部消息队列；当前只固定领域事件 contract。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_notifications.py
scripts/run_tests.sh tests/team_cloud/test_notifications.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_memory_review_api.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/notifications.py team_cloud/backup/storage.py team_cloud/break_glass.py team_cloud/memory/review.py team_cloud/api.py tests/team_cloud/test_notifications.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_memory_review_api.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/notifications.py team_cloud/backup/storage.py team_cloud/break_glass.py team_cloud/memory/review.py team_cloud/api.py tests/team_cloud/test_notifications.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_break_glass.py tests/team_cloud/test_memory_review_api.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
