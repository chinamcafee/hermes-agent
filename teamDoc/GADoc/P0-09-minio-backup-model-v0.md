# P0-09 MinIO key/manifest 规范 v0

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-08 PostgreSQL/pgvector schema v0`

## 目标

冻结 MinIO bucket、object key、manifest 和 PostgreSQL `object_manifests` 映射规则，覆盖个人记忆备份、组织导出、附件、文档原文和恢复 staging。MinIO 只保存对象；对象可见性、权限、checksum、加密状态和生命周期真相在 PostgreSQL。

## 工件

| 工件 | 用途 |
| --- | --- |
| [manifest-v0.schema.json](artifacts/minio/manifest-v0.schema.json) | 对象 manifest JSON Schema。 |
| [personal-backup-manifest.json](artifacts/minio/examples/personal-backup-manifest.json) | 个人记忆备份样例。 |
| [org-export-manifest.json](artifacts/minio/examples/org-export-manifest.json) | 组织导出样例。 |
| [attachment-manifest.json](artifacts/minio/examples/attachment-manifest.json) | 会话附件样例。 |
| [document-source-manifest.json](artifacts/minio/examples/document-source-manifest.json) | 文档原文样例。 |

## Buckets

| Bucket | Object type | 默认访问 |
| --- | --- | --- |
| `hermes-personal-backups` | `personal_backup` | owner-only；break-glass 显式审批后读取。 |
| `hermes-org-exports` | `org_export` | organization owner/admin export 权限。 |
| `hermes-attachments` | `attachment` | session/project 权限。 |
| `hermes-document-sources` | `document_source` | document/project 权限。 |
| `hermes-restore-staging` | `restore_staging` | restore job owner-only，短生命周期。 |

所有 bucket 默认 private，禁止 public policy。下载只通过 Team API 生成短期 presigned URL。

## Object key 规范

| Object type | Key pattern |
| --- | --- |
| `personal_backup` | `org/{org_id}/member/{member_id}/personal-memory/{yyyy}/{mm}/{backup_id}/backup.zip.enc` |
| `org_export` | `org/{org_id}/exports/{yyyy}/{mm}/{export_id}/export.zip.enc` |
| `attachment` | `org/{org_id}/session/{session_id}/attachments/{attachment_id}/blob.bin` |
| `document_source` | `org/{org_id}/documents/{document_id}/source/{source_object_id}/source.bin` |
| `restore_staging` | `org/{org_id}/member/{member_id}/restore/{restore_job_id}/staging.zip.enc` |

规则：

- key 只使用小写路径段、UUID、年份、月份和固定文件名。
- 原始文件名只进入 manifest `source.filename_original`，不进入 key。
- key 中必须包含 `org_id`；personal/restore key 必须包含 `member_id`。
- object key 不承载权限判断，权限由 PostgreSQL + SpiceDB 决定。

## Manifest v0

manifest 必须至少包含：

- `schema_version = 1`
- `object_type`
- `object_id`
- `org_id`
- `owner_member_id` / `team_id` / `project_id` / `session_id` / `document_id`
- `bucket`
- `object_key`
- `content_type`
- `size_bytes`
- `checksum_sha256`
- `encryption`
- `retention`
- `created_at`

`checksum_sha256` 计算加密后的对象 bytes。解密后内容的 checksum 如需保存，放入加密包内部 manifest，避免泄露个人记忆内容特征。

## PostgreSQL 映射

MinIO 写入成功后必须在同一业务流程中写 `object_manifests`：

| Manifest field | PostgreSQL column |
| --- | --- |
| `object_id` | `object_manifests.id` |
| `org_id` | `object_manifests.org_id` |
| `owner_member_id` | `object_manifests.owner_member_id` |
| `bucket` | `object_manifests.bucket` |
| `object_key` | `object_manifests.object_key` |
| `object_type` | `object_manifests.object_type` |
| `checksum_sha256` | `object_manifests.checksum_sha256` |
| `encryption.key_id` | `object_manifests.encryption_key_id` |
| `size_bytes` | `object_manifests.size_bytes` |
| `retention/legal hold` | future retention tables / audit metadata |

PostgreSQL row 是对象存在性的 canonical index。MinIO 孤儿对象由 P3 scanner 发现并隔离。

## 包格式

个人记忆备份对象 `backup.zip.enc` 解密后包含：

```text
manifest.json
memories.jsonl
memory_events.jsonl
README.md
```

组织导出对象 `export.zip.enc` 解密后包含：

```text
manifest.json
organizations.jsonl
members.jsonl
teams.jsonl
projects.jsonl
sessions.jsonl
memory_items.jsonl
documents.jsonl
audit_events.jsonl
```

附件和文档原文不要求 zip 包，但必须有 manifest 和 checksum。

## 生命周期

| Object type | 默认 retention |
| --- | --- |
| `personal_backup` | member policy 控制，默认保留最近 8 份。 |
| `org_export` | 默认 30 天，管理员可提前删除。 |
| `attachment` | 跟随 session/project retention。 |
| `document_source` | 跟随 document retention。 |
| `restore_staging` | 默认 7 天，restore 完成后可提前删除。 |

删除流程必须先写 audit，再删除 MinIO object，最后把 `object_manifests.status` 更新为 `deleted`。删除失败进入 retry/dead letter。

## 安全约束

1. MinIO access key 只给 Team API/worker，用户不直连 MinIO。
2. 所有用户下载通过 presigned URL，TTL 默认 <= 5 分钟。
3. 个人备份默认 envelope encryption；可选用户 passphrase 模式下 Team Cloud 不保存 passphrase。
4. 管理员不能静默读取 `personal_backup`，必须通过 break-glass workflow 生成审计关系。
5. bucket lifecycle 不替代 PostgreSQL retention/audit；两者需要 reconciliation。

## 验证

P0-09 验证样例 manifest 均为合法 JSON，并包含 schema required fields。P1/P3 需要补充 JSON Schema 自动校验和 MinIO put/get smoke。
