# P3-05 Personal backup policy

日期：2026-05-22
状态：Implemented
前置：`P0-08 PostgreSQL schema`、`P0-09 MinIO 备份模型`、`P2-03 Memory CRUD API`

## 目标

本步骤为个人记忆定时备份建立 policy contract：成员可以配置是否启用备份、周期、保留数量、导出范围、加密模式和通知渠道。实现范围限定在 policy service 和 Team Cloud API，不在本步骤实现 JSONL exporter、MinIO upload、restore preview 或 restore execute。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/backup/policy.py` | `BackupPolicyService`，保存个人备份偏好并暴露 scheduler due lookup。 |
| `team_cloud/api.py` | `/v1/me/memory-backup-policy` GET/PUT API。 |
| `tests/team_cloud/test_backup_policy.py` | 覆盖默认策略、upsert、due policy 查询和 API 400。 |
| `teamDoc/GALog/2026-05-22-p3-05-personal-backup-policy.md` | TDD 红绿记录和回归证据。 |

## Policy Contract

默认 policy 不立即开启备份，避免在成员未确认前生成个人数据副本：

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `enabled` | `false` | 是否纳入 scheduler due scan。 |
| `cadence` | `weekly` | 可选 `daily`、`weekly`、`monthly`。 |
| `retention_count` | `8` | 后续 retention cleanup 保留最近 N 个成功备份。 |
| `include_archived` | `false` | 是否导出 archived memory。 |
| `include_deleted` | `false` | 是否导出 deleted memory。 |
| `include_embeddings` | `false` | 是否包含 embedding 载荷。 |
| `encryption_mode` | `org_managed` | 可选 `org_managed` 或 `user_passphrase`。 |
| `notification_channels` | `["in_app"]` | 可选 `email`、`in_app`、`webhook`。 |

`BackupPolicyService.due_policies(at=...)` 只返回 `enabled=true` 且 `next_run_at <= at` 的策略。PUT 启用策略且未传 `next_run_at` 时，会按 cadence 生成下一次运行时间，后续 P3-06/P3-07 worker 可复用这个 contract。

## API

```text
GET /v1/me/memory-backup-policy?org_id=<org>&member_id=<member>
PUT /v1/me/memory-backup-policy
```

PUT body：

```json
{
  "org_id": "org-1",
  "member_id": "alice",
  "cadence": "monthly",
  "enabled": true,
  "retention_count": 12,
  "include_deleted": false,
  "include_embeddings": true,
  "encryption_mode": "org_managed",
  "notification_channels": ["in_app"]
}
```

错误以 HTTP 400 返回稳定 `detail`，例如 `invalid_cadence`、`invalid_retention_count`、`invalid_encryption_mode`。这让 Web Personal Memory 页面可以直接展示字段级错误。

## 非目标

- 不导出 `memory_items` / `memory_events` JSONL。
- 不生成 manifest、checksum 或 envelope encryption 包。
- 不上传 MinIO，也不写 `object_manifests` 和 `backup_jobs`。
- 不实现 restore preview / execute。
- 不实现通知发送；当前仅保存通知偏好。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_backup_policy.py
scripts/run_tests.sh tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/backup/policy.py team_cloud/api.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/backup/__init__.py team_cloud/backup/policy.py team_cloud/api.py tests/team_cloud/test_backup_policy.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
