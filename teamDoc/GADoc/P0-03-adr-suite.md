# P0-03 ADR 套件索引

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-01 GA 范围冻结`、`P0-02 Hermes 代码边界审计`

## ADR 列表

| ADR | 决策 | 状态 |
| --- | --- | --- |
| [ADR-0001](adr/ADR-0001-casdoor-identity.md) | 使用 Casdoor 作为默认身份认证和身份生命周期系统 | Accepted |
| [ADR-0002](adr/ADR-0002-spicedb-authorization.md) | 使用 SpiceDB 作为默认资源级授权系统 | Accepted |
| [ADR-0003](adr/ADR-0003-postgres-pgvector-memory.md) | 使用 PostgreSQL + pgvector 作为 canonical memory 和向量检索底座 | Accepted |
| [ADR-0004](adr/ADR-0004-minio-object-backup.md) | 使用 MinIO 承载个人记忆备份、导出包和对象数据 | Accepted |
| [ADR-0005](adr/ADR-0005-hermes-runtime-integration.md) | 通过 TeamContext、TeamMemoryProvider 和 TeamToolPolicyHook 集成 Hermes runtime | Accepted |

## 共识边界

1. Casdoor 只回答“用户是谁”和身份生命周期，不回答资源是否可访问。
2. SpiceDB 是资源级授权真相，数据库权限快照只能做性能优化或诊断。
3. PostgreSQL 中 `memory_items` 是唯一 canonical memory，pgvector 是第一版默认向量索引。
4. MinIO 对象必须有 PostgreSQL manifest、checksum、owner、retention 和审计记录。
5. Hermes core 保持 runtime 角色，只接受 Team Cloud 注入的上下文和策略 hook，不承载最终企业权限边界。

## 后续依赖

- `P0-04` 组件版本和许可证冻结必须引用 ADR 中的默认组件。
- `P0-05` 本地拓扑设计必须按 ADR 的服务边界拆分 compose service。
- `P0-07` SpiceDB schema v0 必须满足 ADR-0002 的资源模型。
- `P0-08` PostgreSQL/pgvector schema v0 必须满足 ADR-0003 的 canonical memory 规则。
- `P0-09` MinIO 备份模型 v0 必须满足 ADR-0004 的 manifest 和权限规则。
