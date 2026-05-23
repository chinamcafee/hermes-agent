# P1-15 MinIO client 和 manifest

日期：2026-05-22
状态：Implemented
前置：`P1-03 本地 compose 栈`

## 目标

本步骤实现 MinIO 对象访问的最小服务层：bucket bootstrap、对象上传、manifest 生成、checksum 计算和短期 signed URL。当前实现使用内存 object store 固定行为契约，后续可替换为真实 MinIO SDK。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/storage/minio.py` | bucket 映射、内存 object store、manifest service。 |
| `team_cloud/storage/__init__.py` | storage primitives 包导出。 |
| `tests/team_cloud/test_minio_manifest.py` | bucket bootstrap、personal backup manifest、signed URL、必填字段测试。 |

## 行为

- Buckets：
  - `personal_backup` -> `hermes-personal-backups`
  - `org_export` -> `hermes-org-exports`
  - `attachment` -> `hermes-attachments`
  - `document_source` -> `hermes-document-sources`
  - `restore_staging` -> `hermes-restore-staging`
- Object key：
  - 遵循 P0-09 key pattern。
  - key 中包含 `org_id`。
  - personal/restore key 要求 `owner_member_id`。
- Manifest：
  - `schema_version=1`
  - 写入 bucket、object_key、content_type、size、sha256、encryption、retention、created_at。
  - manifest 保存在 service 的 manifest index 中，模拟 PostgreSQL `object_manifests`。
- Signed URL：
  - 默认由 Team API 生成，当前内存实现使用 `memory://` URL。
  - TTL 强制 `<= 5 分钟`。

## 非目标

- 不引入 MinIO SDK。
- 不实现真实网络上传。
- 不实现 envelope encryption。
- 不实现生命周期清理。
- 不实现 object manifest PostgreSQL repository。

## 后续衔接

- P3-05 到 P3-09：个人备份策略、加密 JSONL exporter、MinIO upload/lifecycle、restore preview/execute。
- P4/P5：真实 MinIO smoke、backup/restore drill、runbook。
