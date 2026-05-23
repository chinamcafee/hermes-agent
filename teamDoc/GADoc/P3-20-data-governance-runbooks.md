# P3-20 数据治理 Runbook

日期：2026-05-22
状态：Implemented
前置：`P3-10 组织导出`、`P3-11 删除请求`、`P3-12 Hard delete worker`、`P3-14 Break-glass`、`P3-18 Backup/restore tests`、`P3-19 AuthZ chaos tests`

## 目标

本文档把 P3 已实现的数据治理能力整理成可执行 runbook，覆盖 personal backup/restore/delete、organization export、deletion request/hard delete、break-glass 和 AuthZ 故障处置。它面向本地企业版开箱即用部署，优先描述当前 in-memory contract 和 Team Cloud API 语义，后续 PostgreSQL/MinIO/SpiceDB 真正持久化替换时保持同一操作边界。

## 适用角色

| 角色 | 可执行操作 | 关键约束 |
| --- | --- | --- |
| Org Owner | 组织导出、删除请求审批、break-glass 发起或审批 | 不能静默读取成员 personal memory 或 personal backup。 |
| Security Admin | break-glass 审批、安全事件取证、AuthZ chaos 排障 | 必须写 audit 和工单号。 |
| Member | personal backup 创建、下载、恢复、删除 | 只能操作本人 personal memory 和 backup。 |
| SRE | foundation smoke、备份恢复演练、MinIO/SpiceDB/outbox 故障恢复 | 不绕过 Team Cloud 权限策略。 |

## Personal Backup Runbook

### Pre-checks

- 确认成员、组织和 project identity 已同步，personal memory 查询必须限定 `org_id` 和 `subject_member_id`。
- 确认 backup policy 已配置，参考 `team_cloud/backup/policy.py` 和 `tests/team_cloud/test_backup_policy.py`。
- 确认 object manifest、backup job、restore job 目标存储可写。
- 高敏感场景先检查 `/api/audit/export`，确认没有未关闭的 break-glass 或 deletion request。

### Execution

1. 使用 `PersonalMemoryBackupExporter` 生成 encrypted `backup.zip.enc` 和 manifest。
2. 使用 `PersonalBackupStorageService` 上传对象并写 object manifest。
3. 使用 signed download URL 下载备份包，URL 只给 owner 或经 break-glass 授权的 reviewer。
4. 使用 `RestorePreviewService` 生成 preview，确认新增、跳过、冲突和覆盖项。
5. 使用 `RestoreExecutionService` 执行 merge/overwrite/archive-old 策略。
6. 对演练环境可直接运行 `PersonalBackupRestoreDrill` 串联 export、upload、download、preview 和 execute。

### Validation

- `tests/team_cloud/test_backup_restore_drill.py` 必须通过。
- `tests/team_cloud/test_backup_exporter.py`、`tests/team_cloud/test_backup_storage.py`、`tests/team_cloud/test_restore_preview.py`、`tests/team_cloud/test_restore_execute.py` 必须通过。
- checksum mismatch 必须在 preview 前返回 `checksum_mismatch`，不能创建 restore job。
- 恢复后 embedding rebuild id、memory event 和 audit evidence 必须可追踪。

### Rollback / Recovery

- preview 阶段失败：删除 restore staging object，保留 failed audit。
- execute 阶段失败：保留 restore job 状态和 partial item 列表，禁止静默重试覆盖。
- checksum mismatch：重新生成备份或从另一个 backup manifest 恢复，不允许人工改 checksum。
- MinIO unavailable：暂停 backup policy 调度，记录 backup failure 通知事件，待 P3-21 通知系统承接。

### Evidence

- backup id、object manifest id、checksum、signed URL 过期时间。
- backup job、restore preview、restore job、restored source memory ids。
- audit event：backup.create、backup.read、backup.restore、backup.delete。

## Organization Export Runbook

### Pre-checks

- 操作者必须通过 `org.audit.read` 或组织 owner/security admin 授权。
- 导出前确认是否有进行中的 deletion request；如有，先冻结删除窗口。
- 确认 relationship outbox 没有 `relationship_outbox_dead_letter`，否则导出的 SpiceDB snapshot 可能不是最新状态。

### Execution

1. 使用 `OrganizationExportService` 为目标 org 生成 snapshot。
2. 导出 org/team/project/member metadata。
3. 导出 sessions/messages/tool calls。
4. 导出 memory_items/memory_events。
5. 导出 SpiceDB relationships snapshot。
6. 导出 audit events，并对 token、password、secret、credential、private key 元数据递归脱敏。
7. 上传为 org export object，保留 manifest 和 checksum。

### Validation

- `tests/team_cloud/test_org_export.py` 必须通过。
- 导出包必须包含 `manifest.json`、metadata、sessions、memory、relationships 和 audit JSONL。
- 任意跨 org 数据不得出现在 snapshot 中。
- audit metadata 中 secret-like key 必须被 redacted。

### Rollback / Recovery

- 导出失败：删除未完成 object manifest，记录 failed audit。
- 回灌验证失败：保留 export object，不执行 hard delete，等待 P4 组织导出回灌演练。
- relationship snapshot 过旧：先处理 outbox pending/dead letter，再重新导出。

### Evidence

- export id、org id、object manifest id、checksum、item counts。
- `/api/audit/export` 导出的取证 JSONL。
- foundation smoke 输出和 export package manifest。

## Deletion Request Runbook

### Pre-checks

- 删除目标必须是 member/project/org 中之一，且已完成影响范围确认。
- 如果策略要求 export then delete，先完成 Organization Export Runbook。
- 确认 legal hold 和 retention policy，不允许 hard delete 受保留的数据。
- 确认审批人和执行人不是同一个需要隔离的角色。

### Execution

1. 使用 `DeletionRequestService` 创建 deletion request。
2. 填写 reason、ticket、target type、target id、scheduled_at 和 export_before_delete。
3. 审批后进入 ready_for_worker。
4. `HardDeleteWorker` 执行 disable access、relationship cleanup、canonical row cleanup 和 object manifest cleanup。
5. 完成后写 final audit。

### Validation

- `tests/team_cloud/test_deletion_request.py` 必须通过。
- `tests/team_cloud/test_hard_delete_worker.py` 必须通过。
- member 删除必须禁用成员访问并写 relationship outbox delete。
- org/project 删除必须清理 sessions、memory、tool calls、object manifest 和 relationship snapshot。

### Rollback / Recovery

- scheduled 前取消：将 request 标记为 cancelled，保留审批记录。
- worker failed：保留 failed 状态和 last_error，修复根因后按 idempotency key 重试。
- worker dead letter：停止相关资源发布，检查 `relationship_outbox_dead_letter` 和 object manifest deletion 状态。
- 误删风险：如已完成 export then delete，使用 export package 进入 P4 回灌演练；未导出时不承诺恢复。

### Evidence

- deletion request id、审批记录、reason、ticket、scheduled_at。
- hard delete worker summary：processed、completed、failed、dead_letter。
- final audit event 和 object manifest deletion state。

## Break-glass Runbook

### Pre-checks

- 只用于安全事件、法律/合规请求或 owner 明确授权的紧急排障。
- 必须有 reason、ticket、resource type、resource id、time window 和双人审批。
- 默认通知被访问成员；延迟通知必须有安全或法律策略依据。

### Execution

1. 使用 `BreakGlassService` 创建 request。
2. Owner 和 Security Admin 组合审批，审批人不能绕过职责分离。
3. 创建短期 SpiceDB relationship，例如 backup approved_break_glass_reader。
4. 在窗口内执行读取或取证操作。
5. 到期自动撤销 relationship，并写访问 audit。

### Validation

- `tests/team_cloud/test_break_glass.py` 必须通过。
- 过期 request 必须撤销短期 relationship。
- personal memory/personal backup 的读取必须有 break-glass audit。
- `P3-15 Permission Explorer GA` 应展示 relationship path 和 recent changes。

### Rollback / Recovery

- 审批错误：立即 revoke relationship，标记 request revoked，通知 owner/member。
- 访问超范围：触发安全事件，冻结相关 service account/PAT，导出 audit。
- 通知失败：进入 P3-21 通知系统补偿队列；不得因此隐藏 audit。

### Evidence

- break-glass request id、审批人、reason、ticket、resource scope、expires_at。
- relationship outbox item、permission explorer recent changes。
- audit event：break_glass.requested、break_glass.approved、break_glass.accessed、break_glass.expired。

## Audit And Evidence

### Pre-checks

- 每个治理操作必须带 request id、actor、org id、resource 和 decision。
- 敏感读取、高危工具和 break-glass 访问必须写入 audit。
- 需要导出取证时使用 `/api/audit/export`，并按 org/action/actor/resource/time 过滤。

### Execution

1. 操作前记录 request/ticket。
2. 操作中保留 service result 和 object manifest id。
3. 操作后导出 audit JSONL 并保存到工单。
4. 对高危工具或 AuthZ 故障，关联 `tests/team_cloud/test_authz_chaos.py` 的 fail-closed 证据。

### Validation

- `tests/team_cloud/test_audit_advanced.py` 必须通过。
- audit export 必须是 `application/x-ndjson`，且 secret-like metadata 被 redacted。
- sensitive reads 和 high-risk tools 专项视图必须可复现。

### Rollback / Recovery

- audit write failed：治理操作应 fail closed 或标记 `audit_unavailable`。
- audit export failed：不得删除原始 audit events；修复过滤或序列化后重试。

### Evidence

- audit event id、request id、ticket、export filter、export checksum。
- smoke run id 或本地命令输出摘要。

## Failure Handling

| 故障 | 期望行为 | 排查入口 | 恢复动作 |
| --- | --- | --- | --- |
| `authorization_unavailable` | 管理 API、chat run 和高危工具 fail closed | `tests/team_cloud/test_authz_chaos.py`、`team_cloud/authz/middleware.py` | 恢复 SpiceDB 后重试，不把 outage 当普通 deny 处理。 |
| `relationship_outbox_dead_letter` | 相关资源停止发布或执行敏感操作 | `RelationshipOutboxService.fail_closed_status()` | 修复 writer 错误，重放 outbox 或创建补偿关系。 |
| `checksum_mismatch` | restore preview 前阻断 | `PersonalBackupRestoreDrill.run_checksum_mismatch_guard()` | 换用可信 backup 或重新生成备份。 |
| MinIO upload/download failure | backup/export job failed，保留 audit | `team_cloud/backup/storage.py`、object manifest | 恢复存储后按 idempotency key 重试。 |
| hard delete worker dead letter | 删除请求不标 completed | `HardDeleteWorker` summary | 停止后续删除，修复 canonical cleanup 或 object cleanup。 |
| break-glass abuse | revoke relationship，安全事件升级 | Permission Explorer、audit export | 冻结 actor，通知成员，导出证据。 |

## Validation Matrix

| 领域 | 命令 |
| --- | --- |
| Foundation smoke | `scripts/team-cloud-foundation-smoke.sh` |
| Backup restore drill | `scripts/run_tests.sh tests/team_cloud/test_backup_restore_drill.py` |
| Organization export | `scripts/run_tests.sh tests/team_cloud/test_org_export.py` |
| Deletion request | `scripts/run_tests.sh tests/team_cloud/test_deletion_request.py` |
| Hard delete worker | `scripts/run_tests.sh tests/team_cloud/test_hard_delete_worker.py` |
| Break-glass | `scripts/run_tests.sh tests/team_cloud/test_break_glass.py` |
| AuthZ chaos | `scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py` |
| Data governance docs | `scripts/run_tests.sh tests/team_cloud/test_data_governance_docs.py` |

## 交接说明

- P3-21 通知系统应接入 backup failure、break-glass、review backlog 和 hard delete worker dead letter 通知。
- P4 的真实 chaos drills 和 backup restore drills 需要把本文档中的 in-memory contract 替换为真实 PostgreSQL、SpiceDB 和 MinIO 运行证据。
- P5 Runbook 汇总可直接引用本文档，并补充 upgrade/rollback/offline bundle 操作。
