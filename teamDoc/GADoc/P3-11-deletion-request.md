# P3-11 删除请求

日期：2026-05-22
状态：Implemented
前置：`P3-10 组织导出`

## 目标

本步骤实现数据删除请求的治理层 contract：支持 member、project、org 三类目标的删除申请，支持 `anonymize`、`soft_delete`、`hard_delete` 三种模式，支持删除前绑定组织导出，并把审批、定时触发、worker handoff 和 audit 事件串起来。真实 PostgreSQL、SpiceDB、MinIO 清理不在本步骤执行，由 P3-12 hard delete worker 承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/deletion.py` | `DataDeletionRequestService`，维护删除请求生命周期和执行计划。 |
| `tests/team_cloud/test_deletion_request.py` | 覆盖请求、审批、scheduled due、worker handoff、audit 和非法输入。 |
| `teamDoc/GALog/2026-05-22-p3-11-deletion-request.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `deletion_request` domain。 |

## 生命周期

```text
pending_approval
  -> scheduled
  -> ready_for_worker
  -> completed
```

`create_request()` 固定写入 `data_deletion.requested` audit；`approve_request()` 写入 `data_deletion.approved`；`run_due_requests()` 只把到期且已审批的请求转为 `ready_for_worker`，并写入 `data_deletion.ready_for_worker`。`mark_completed()` 只允许 worker handoff 之后调用，避免未审批请求被直接完成。

## 执行计划

`hard_delete` 的 worker contract 为：

```text
disable_access
export_before_delete
delete_relationships
soft_delete_rows
delete_objects
hard_delete_rows_after_retention
write_final_audit
```

当请求未启用 `export_before_delete` 时，执行计划不会包含 `export_before_delete`。`anonymize` 和 `soft_delete` 保持最小计划，分别只表达匿名化或软删除写入与 final audit。

## 非目标

- 不执行真实数据库硬删除。
- 不删除 SpiceDB relationship。
- 不删除 MinIO object。
- 不实现 retention 窗口和 object lifecycle 清理。
- 不实现后台 worker 重试、死信和幂等锁。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_deletion_request.py
scripts/run_tests.sh tests/team_cloud/test_deletion_request.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/deletion.py tests/team_cloud/test_deletion_request.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/deletion.py tests/team_cloud/test_deletion_request.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
