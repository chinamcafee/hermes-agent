# ADR-0004：使用 MinIO 承载对象和个人记忆备份

状态：Accepted
日期：2026-05-22
适用阶段：P1-P5

## 背景

GA 版本必须让成员自行定时备份、下载、恢复和删除个人记忆，同时支持组织导出、附件、文档原文和 restore staging。对象数据需要私有化部署、生命周期策略、checksum、短期 signed URL 和恢复演练。

## 决策

使用 MinIO 作为默认对象存储。所有对象必须有 PostgreSQL `object_manifests` 记录，包含 `org_id`、owner、bucket、object key、类型、大小、checksum、encryption key、retention、legal hold、状态和审计。

默认桶：

- `hermes-personal-backups`
- `hermes-org-exports`
- `hermes-attachments`
- `hermes-document-sources`
- `hermes-restore-staging`

个人记忆备份默认使用 envelope encryption，备份包包含 manifest、memories JSONL、memory events JSONL 和 README。管理员不能静默读取个人备份；break-glass 必须双人审批并审计。

## 备选

| 方案 | 结果 |
| --- | --- |
| 直接写本地文件系统 | 不利于分布式部署、生命周期、signed URL 和对象级恢复演练 |
| 云厂商 S3 作为唯一默认 | 私有化客户可用性和源码可访问约束不稳定；可作为兼容目标，不作为默认 |
| 只依赖 PostgreSQL bytea | 备份包、附件、文档原文和大对象生命周期管理成本高 |

## 后果

- P1 必须提供 MinIO compose service、bucket bootstrap、client 和 manifest API。
- P3 必须提供 backup policy、加密 exporter、upload/lifecycle、restore preview 和 restore execute。
- 所有下载必须使用短期 signed URL。
- checksum mismatch 必须阻止恢复。
- MinIO AGPL-3.0 许可证需要进入 P0-04 和 P5 legal/compliance package。

## 回滚条件

若目标客户许可证或部署规范不接受 MinIO，允许保留 S3-compatible object store 抽象并替换实现。但对象 manifest、key 规范、checksum、审计、权限和 restore staging 语义不得回滚。
