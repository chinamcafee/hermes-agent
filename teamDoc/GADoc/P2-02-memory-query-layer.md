# P2-02 pgvector 查询层

日期：2026-05-22
状态：Implemented
前置：`P2-01 记忆迁移表`、`P1-09 SpiceDB client`

## 目标

本步骤实现 memory query layer 的可测试切片，固定 personal/team_shared 两条召回边界。当前实现使用内存 repository 模拟 pgvector 排序，并输出 SQL explain plan；真实 PostgreSQL repository 留给后续接入。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/query.py` | Memory item、query result、内存 query repository、query service、pgvector explain。 |
| `team_cloud/memory/__init__.py` | memory package 导出。 |
| `tests/team_cloud/test_memory_query_layer.py` | personal 隔离、team AuthZ batch check、query explain 测试。 |

## 行为

- Personal query：
  - 必须匹配 `org_id`。
  - 必须 `scope=personal`。
  - 必须 `subject_member_id=current_member_id`。
  - 只返回 `status=active`。
  - 记录 `read_memory_ids`。
- Team query：
  - 必须匹配 `org_id`、`team_id`、可选 `project_id`。
  - 必须 `scope=team_shared`。
  - 只返回 `status=active`。
  - 候选结果经过 `SpiceDB batch_check(memory#read_team)`。
  - 未配置 `authz_client` 时 fail closed，返回空结果。
- pgvector explain：
  - 展示 `memory_embeddings.embedding <=> :query_embedding`。
  - 标注 `idx_memory_embeddings_hnsw` 和 `idx_memory_items_scope_type_status`。
  - team query 明确后置 `spicedb batch_check(memory#read_team)`。

## 非目标

- 不连接真实 PostgreSQL。
- 不实现 `/v1/memory/prefetch` API。
- 不做 rerank 或 token budget formatting。
- 不实现 performance baseline；`P2-21` 承接。

## 后续衔接

- `P2-03`：Memory CRUD API 使用 query layer 的边界模型。
- `P2-04`：Prefetch pipeline 在 query result 上做分区、rerank 和格式化。
- `P2-20`：扩展 Alice/Bob、org A/B、team/project 隔离测试。
