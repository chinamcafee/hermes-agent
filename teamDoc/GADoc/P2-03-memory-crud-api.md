# P2-03 Memory CRUD API

日期：2026-05-22
状态：Implemented
前置：`P2-01 记忆迁移表`

## 目标

本步骤实现 Memory CRUD API 的最小可测试切片，覆盖 list、create、update、soft delete、archive、restore 和事件记录。当前实现使用 `InMemoryMemoryService` 固定行为契约，后续可替换为 PostgreSQL repository。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/service.py` | In-memory Memory CRUD service、checksum、scope validation、events。 |
| `team_cloud/api.py` | 挂载 `/v1/memory` API。 |
| `tests/team_cloud/test_memory_crud_api.py` | create/list、update version、delete/restore、team pending review 测试。 |

## API

- `GET /v1/memory`
  - filter：`org_id`、`scope`、`status`、`memory_type`、`sensitivity`。
- `POST /v1/memory`
  - 创建 personal 或 team_shared memory。
- `PATCH /v1/memory/{memory_id}`
  - 更新 content、type、sensitivity 或 status。
- `DELETE /v1/memory/{memory_id}`
  - soft delete，写 delete event。
- `POST /v1/memory/{memory_id}/archive`
  - archive，写 archive event。
- `POST /v1/memory/{memory_id}/restore`
  - restore，写 restore event。

## 行为

- personal memory：
  - 要求 `subject_member_id`。
  - 禁止 `team_id`。
  - 默认 `status=active`。
- team_shared memory：
  - 要求 `team_id`。
  - 禁止 `subject_member_id`。
  - 默认 `status=pending_review`。
- update：
  - content 更新会重算 `normalized_content` 和 `checksum_sha256`。
  - `version` 自增。
- events：
  - create/update/delete/archive/restore 均写入 service 的事件列表。

## 非目标

- 不连接 PostgreSQL。
- 不做 SpiceDB write relationships。
- 不实现 review queue API；`P2-08` 承接。
- 不实现 hard delete；P3 governance worker 承接。

## 后续衔接

- `P2-04`：prefetch pipeline 读取 CRUD/API 写入的 memory。
- `P2-08`：review queue 处理 `pending_review` team_shared memory。
- `P3-11/P3-12`：delete request 和 hard delete worker 接管永久删除。
