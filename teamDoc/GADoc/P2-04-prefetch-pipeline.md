# P2-04 Prefetch pipeline

日期：2026-05-22
状态：Implemented
前置：`P2-02 pgvector 查询层`、`P2-03 Memory CRUD API`

## 目标

本步骤实现 memory prefetch pipeline 的最小可测试切片，覆盖 query embedding、personal/team_shared 分区召回、team AuthZ 过滤和 memory IDs 记录，并通过 `/v1/memory/prefetch` 暴露。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/prefetch.py` | Embedding provider 协议、static provider、prefetch pipeline。 |
| `team_cloud/api.py` | 注入 `memory_prefetch_pipeline` 时挂载 `/v1/memory/prefetch`。 |
| `tests/team_cloud/test_memory_prefetch_pipeline.py` | pipeline 分区输出和 API route 测试。 |

## 行为

- 调用 embedding provider 将 query 转为 query embedding。
- 调用 `MemoryQueryService.query_personal()` 获取 personal 分区。
- 调用 `MemoryQueryService.query_team()` 获取 team_shared 分区，并复用 team query 的 SpiceDB batch check。
- 返回：
  - `partitions`: personal/team_shared 分区。
  - `memory_ids`: 本次召回的 memory id 列表。
  - 每条 item 的 id、scope、memory_type、sensitivity、content。

## 非目标

- 不实现 rerank。
- 不实现 token budget trimming。
- 不接入真实 embedding provider。
- 不实现 performance baseline；`P2-21` 承接。

## 后续衔接

- `P2-11` TeamMemoryProvider 调用 `/v1/memory/prefetch`。
- `P2-13` sync_turn observation 和 prefetch 共同形成双层记忆闭环。
- `P2-20` 扩展隔离测试套件。
