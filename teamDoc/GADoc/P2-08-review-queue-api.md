# P2-08 Review Queue API

日期：2026-05-22
状态：Implemented
前置：`P2-07 Memory extraction worker`

## 目标

本步骤实现 memory review queue 的最小可测试 API。API 支持按组织和 review kind 查询 pending review item，支持 approve、reject，以及 approve 前编辑候选内容，并把审核动作写入 audit log。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/review.py` | review queue service、状态转移、业务 audit。 |
| `team_cloud/api.py` | 注入 `memory_review_service` 时挂载 `/v1/memory/review` API。 |
| `team_cloud/memory/__init__.py` | 导出 review service primitives。 |
| `tests/team_cloud/test_memory_review_api.py` | list、approve with edit-before-approve、reject 和 audit 测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 review API 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-08 测试纳入本地 smoke 回归。 |

## API

- `GET /v1/memory/review`
  - 参数：`org_id`、`status`、`review_kind`、`limit`。
  - 返回：`{"items": [...]}`。
- `POST /v1/memory/review/{review_id}/approve`
  - 必填：`actor_member_id`。
  - 可选：`content`、`memory_type`、`sensitivity`，用于 edit-before-approve。
  - 行为：review item -> `approved`，memory -> `active`。
- `POST /v1/memory/review/{review_id}/reject`
  - 必填：`actor_member_id`。
  - 可选：`reason`。
  - 行为：review item -> `rejected`，memory -> `rejected`。

## 行为

- 只允许 pending review item approve/reject；非 pending 返回冲突。
- approve 会调用 Memory CRUD update，保留版本自增和 memory event 记录。
- reject 会把候选 memory 标记为 `rejected`。
- audit action：
  - `memory.review.approved`
  - `memory.review.rejected`
- audit metadata 记录 `memory_id`、是否编辑和拒绝原因。

## 非目标

- 不实现前端 Review Queue 页面。
- 不实现 SpiceDB `memory#review` 权限中间件；后续与 AuthZ middleware 集成。
- 不实现 duplicate/conflict/PII detector；P2-09/P2-10 承接。
- 不实现 reviewer 分配策略。

## 后续衔接

- P2-09：duplicate/conflict detector 写入 review item 并复用本 API。
- P2-10：PII/secret detector 写入 `review_kind=pii` 或拒绝候选。
- P2-11/P2-12：TeamMemoryProvider tools 可调用 review API。
- P2-17：Web Chat/Admin UI 可展示 review queue。
