# ADR-0003：使用 PostgreSQL + pgvector 作为 canonical memory 底座

状态：Accepted
日期：2026-05-22
适用阶段：P1-P5

## 背景

企业版需要个人记忆和团队共享记忆两级隔离，并支持审核、来源追踪、版本、敏感级别、导出、删除、备份恢复和审计。现有第三方 memory provider 可以继续作为可选扩展，但不能承担 canonical memory 或企业权限边界。

## 决策

使用 PostgreSQL 作为 canonical data store，使用 pgvector 作为第一版默认向量检索能力。`memory_items` 保存正文、scope、owner/team、状态、来源、敏感级别、checksum 和版本；`memory_embeddings` 保存 embedding；`memory_events`、`memory_observations`、`memory_review_items` 支撑审计、抽取和审核。

默认只承诺两级记忆：

- `personal`：`org_id + subject_member_id` 强绑定，只影响本人。
- `team_shared`：`org_id + team_id + optional project_id`，审核后可被授权团队/项目召回。

## 备选

| 方案 | 结果 |
| --- | --- |
| 独立向量库作为默认 | 检索能力强，但早期会增加事务一致性、备份恢复、权限过滤和运维复杂度 |
| 第三方 memory SaaS 作为 canonical | 不满足私有化、权限边界、导出删除和备份恢复目标 |
| 只用 Hermes 本地 MEMORY.md | 无法表达 org/member/team scope、审核、审计和恢复 |

## 后果

- P1/P2 migrations 必须覆盖 identity、conversation、memory、backup、authz outbox 和 audit 分层。
- 所有 memory query 必须强制 `org_id`，personal query 必须强制 `subject_member_id = current_member_id`。
- team_shared 检索必须先按 org/team/project 粗过滤，再做 SpiceDB check。
- embedding 模型切换需保留模型版本，维度变化使用新 `embedding_model`。
- 需要 pgvector query explain、HNSW/IVFFlat 策略、prefetch P95 和 bulk import 索引策略。

## 回滚条件

只有当 pgvector 在 GA 目标租户规模下无法达到 prefetch P95 或运维要求时，才评估拆分独立向量库。即使拆分，PostgreSQL 中的 `memory_items` 仍保留 canonical truth，独立向量库只作为派生索引。
