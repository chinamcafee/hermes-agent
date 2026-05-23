# P1-11 Relationship outbox

日期：2026-05-22
状态：Implemented
前置：`P1-09 SpiceDB client`

## 目标

本步骤实现 SpiceDB relationship outbox 的服务层和 worker 行为契约。业务写入方通过幂等 key 入队 relationship mutation；worker 顺序处理 pending/failed 项，成功标记 applied，失败记录 attempts 和 last_error，超过阈值进入 dead letter。相关资源在 outbox 未 applied 前保持 fail closed。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/outbox.py` | outbox item、内存 repository、enqueue service、worker。 |
| `team_cloud/authz/__init__.py` | 导出 outbox primitives。 |
| `tests/team_cloud/test_relationship_outbox.py` | 幂等入队、成功应用、失败重试、dead letter、fail-closed 测试。 |

## 行为

- 入队：
  - 支持 typed `Relationship` 或已格式化 relationship string。
  - 生成稳定 `idempotency_key`，相同 org/aggregate/operation/relationships 返回同一 item。
  - 空 relationships 被拒绝。
- Worker：
  - 处理 `pending` 和 `failed`。
  - 成功后标记 `applied` 并设置 `processed_at`。
  - 失败后 attempts +1。
  - attempts 达到 `max_attempts` 后标记 `dead_letter`。
- Fail closed：
  - 同一 aggregate 存在非 `applied` outbox item 时，`requires_fail_closed()` 返回 true。
  - 后续 AuthZ middleware 可据此拒绝敏感读取或高危操作。

## 非目标

- 不直接连接 PostgreSQL。
- 不实现 `SELECT FOR UPDATE SKIP LOCKED`。
- 不实现指数退避调度器。
- 不实现告警或 dead letter 管理 API。

## 后续衔接

- P1-12：AuthZ middleware 使用 fail-closed 判断。
- P1-13：组织/团队/成员 API 在业务事务内写 outbox。
- P1-14：失败、dead letter、敏感拒绝进入 audit。
- P1-21/P4：dead letter 和 outbox lag 纳入观测指标。
