# P2-01 记忆迁移表

日期：2026-05-22
状态：Implemented
前置：`P1-04 PostgreSQL 基础迁移`

## 目标

本步骤在 P0/P1 基础 schema 上追加 P2 memory runtime migration。`001_schema_v0.sql` 已创建 `memory_items`、`memory_embeddings`、`memory_events`、`memory_observations`、`memory_review_items` 和 HNSW index；P2-01 补齐运行期需要的 memory type、source event link、extraction trace、confidence、review kind 和 pending indexes。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/sql_migrations/002_memory_runtime_schema.sql` | P2 memory runtime schema refinement。 |
| `team_cloud/sql_migrations/002_memory_runtime_schema.rollback.md` | 本地/dev rollback note。 |
| `deploy/team-cloud/compose.yaml` | `team-migrate` 改为挂载并按顺序应用全部 SQL migration。 |
| `tests/team_cloud/test_memory_migrations.py` | 002 migration 和 rollback note 测试。 |
| `tests/team_cloud/test_postgres_migrations.py` | migration runner、checksum、compose 全量迁移测试更新。 |

## Schema 变更

`memory_items`：

- `memory_type`: `fact`、`preference`、`procedure`、`constraint`、`summary`。
- `source_event_id`: 指向 `memory_events(id)`，用于后续版本更新和 trace。
- `idx_memory_items_scope_type_status`: 支撑 P2-03 list filter 和 P2-02 query prefilter。

`memory_observations`：

- `extraction_trace`: 保存 extraction worker 中间数据。
- `confidence`: 候选置信度，范围 `0..1`。
- `idx_memory_observations_pending`: 支撑 extraction worker 扫描 pending/processing。

`memory_review_items`：

- `review_kind`: `team_candidate`、`pii`、`duplicate`、`conflict`。
- `candidate_payload`: 保存 review 前候选内容和 detector 元数据。
- `confidence`: 审核候选置信度。
- `idx_memory_review_pending_kind`: 支撑 review queue 按类型拉取 pending items。

## Migration 行为

- `MigrationRunner.default().plan()` 按文件名顺序发现所有 `*.sql`。
- `team-migrate` compose job 挂载 `../../team_cloud/sql_migrations:/migrations:ro`。
- `team-migrate` 使用 `for migration in /migrations/*.sql` 顺序应用 migration。

## 非目标

- 不实现 pgvector query 层；`P2-02` 承接。
- 不实现 Memory CRUD API；`P2-03` 承接。
- 不实现 embedding/extraction worker；`P2-06/P2-07` 承接。
- 不实现 memory relationship 写入 SpiceDB；`P2-05` 承接。

## 后续衔接

- `P2-02`：基于 `memory_type`、scope/status/sensitivity 和 HNSW index 实现查询层。
- `P2-03`：Memory CRUD API 使用新增字段做 filter 和事件 trace。
- `P2-07/P2-08/P2-09`：extraction、review、duplicate/conflict detector 使用 `candidate_payload`、`confidence` 和 `review_kind`。
