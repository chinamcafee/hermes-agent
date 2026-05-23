# P3-12 Hard delete worker

日期：2026-05-22
状态：Implemented
前置：`P3-11 删除请求`

## 目标

本步骤实现删除请求的 worker handoff：从 P3-11 的 `ready_for_worker` 请求中取出待执行项，按目标类型清理 SpiceDB relationship、PostgreSQL canonical rows 和 MinIO object manifest，并在完成或失败时写入 audit。当前实现保持 in-memory repository contract，后续可以替换为 PostgreSQL repository、SpiceDB client 和真实 MinIO SDK。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/deletion_worker.py` | `HardDeleteWorker`，执行清理、失败重试和 dead letter。 |
| `tests/team_cloud/test_hard_delete_worker.py` | 覆盖 member hard delete 成功路径与 MinIO 失败重试路径。 |
| `teamDoc/GALog/2026-05-22-p3-12-hard-delete-worker.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `hard_delete_worker` domain。 |

## Worker Contract

`HardDeleteWorker.process_ready(limit=100)` 只处理 `ready_for_worker` 和 `worker_failed` 请求。每个请求按以下顺序执行：

```text
disable_access
soft_delete_rows
delete_objects
hard_delete_rows_after_retention
mark_completed
```

`disable_access` 使用 relationship snapshot 写入 relationship outbox 的 delete 操作；member 目标如果存在于 `InMemoryOrganizationService`，会先调用 `disable_member()` 触发成员关系删除，再在 hard delete 阶段删除成员记录。

## Target Scope

- `member`：匹配 `id`、`member_id`、`owner_member_id`、`subject_member_id`、`created_by_member_id`。
- `project`：匹配 `id` 或 `project_id`。
- `org`：匹配请求 `org_id` 范围内全部记录。

当前覆盖的 canonical rows 包括 memory items/events、cloud sessions、org members/teams/orgs。MinIO 对象通过 `ObjectManifestService.mark_deleted()` 删除 object bytes 并保留 manifest deletion state。

## Retry And Dead Letter

worker 捕获单个请求处理异常，不阻断批次内其他请求。失败后写回：

```text
status = worker_failed | dead_letter
worker_attempts
last_error
updated_at
```

未达到 `max_attempts` 时下一轮会重试；达到上限后标记 `dead_letter` 并写 `data_deletion.worker_dead_letter` audit。失败或 dead letter 都不会设置 `completed_at`。

## 非目标

- 不连接真实 PostgreSQL。
- 不调用真实 SpiceDB WriteRelationships。
- 不调用真实 MinIO SDK。
- 不实现 retention policy 计算；本步骤只执行 P3-11 交付的 worker plan。
- 不实现跨进程锁、批次调度器或 dead letter 后台页面。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_hard_delete_worker.py
scripts/run_tests.sh tests/team_cloud/test_deletion_request.py tests/team_cloud/test_hard_delete_worker.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/deletion_worker.py tests/team_cloud/test_hard_delete_worker.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/deletion_worker.py tests/team_cloud/test_hard_delete_worker.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
