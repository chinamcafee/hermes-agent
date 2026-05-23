# GALog 2026-05-22 P0-09 MinIO 备份模型 v0

## 工作粒度

- 工作包：`P0-09 MinIO 备份模型 v0`
- 类型：对象存储规范 / manifest 设计
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/15-minio-personal-backup.md`
- `teamDoc/GADoc/adr/ADR-0004-minio-object-backup.md`
- `teamDoc/GADoc/P0-05-local-topology-design.md`
- `teamDoc/GADoc/P0-08-postgres-pgvector-schema-v0.md`

## 产出

- 新增：`teamDoc/GADoc/artifacts/minio/manifest-v0.schema.json`
- 新增：`teamDoc/GADoc/artifacts/minio/examples/personal-backup-manifest.json`
- 新增：`teamDoc/GADoc/artifacts/minio/examples/org-export-manifest.json`
- 新增：`teamDoc/GADoc/artifacts/minio/examples/attachment-manifest.json`
- 新增：`teamDoc/GADoc/artifacts/minio/examples/document-source-manifest.json`
- 新增：`teamDoc/GADoc/P0-09-minio-backup-model-v0.md`

## 执行记录

1. 核对 P0-09 要求：个人备份、组织导出、附件、文档原文的 key/manifest 规范。
2. 固定五个 bucket，补充 restore staging，保持 P0-05 拓扑一致。
3. 将原始文件名移出 object key，只保留在 manifest source metadata。
4. 定义 manifest v0 JSON Schema 和四类样例 manifest。
5. 明确 `object_manifests` 是对象 canonical index，MinIO 不承载权限真相。

## 决策摘要

1. 个人备份 key 使用 `backup.zip.enc`，解密后包含 manifest、memories、events、README。
2. 组织导出 key 使用 `export.zip.enc`，默认 30 天 retention。
3. 附件和文档原文允许保持原始 content type，但 key 使用固定 `blob.bin` / `source.bin`。
4. `checksum_sha256` 计算加密后 bytes；明文 checksum 如需存在，只放加密包内部。
5. presigned URL 由 Team API 生成，默认 TTL <= 5 分钟。

## 验证计划

- 校验所有样例 manifest 是合法 JSON。
- 检查样例 manifest 包含 schema required fields。
- 检查文档包含 bucket、key pattern、manifest、PostgreSQL 映射、安全约束。
- 验证后更新 `progress-tracker.md` 中 `P0-09` 为 `Done`。

## 验证结果

```text
manifest-v0.schema.json ok
attachment-manifest.json ok
document-source-manifest.json ok
org-export-manifest.json ok
personal-backup-manifest.json ok

attachment-manifest.json: required_fields_ok object_type=attachment
document-source-manifest.json: required_fields_ok object_type=document_source
org-export-manifest.json: required_fields_ok object_type=org_export
personal-backup-manifest.json: required_fields_ok object_type=personal_backup
```

## 后续

- 进入 `P0-10 GA 验收矩阵`。
