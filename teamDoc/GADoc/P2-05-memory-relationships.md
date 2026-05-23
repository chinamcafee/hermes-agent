# P2-05 Memory relationships

日期：2026-05-22
状态：Implemented
前置：`P1-11 Relationship outbox`

## 目标

本步骤把 memory runtime 的业务对象映射到 SpiceDB relationship，并通过 P1-11 outbox 进行幂等写入。目标是让 personal memory、team_shared memory 和 reviewer/curator 路径都具备可审计、可重试、fail-closed 的 relationship 写入入口。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/memory/relationships.py` | Memory relationship 规划和 outbox 入队服务。 |
| `team_cloud/memory/service.py` | `InMemoryMemoryService` 创建 memory 时可选触发 relationship 入队。 |
| `tests/team_cloud/test_memory_relationships.py` | personal owner、team parent/project、curator reviewer 和缺失上下文拒绝测试。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 将 memory relationship 检查纳入 smoke matrix。 |
| `scripts/team-cloud-foundation-smoke.sh` | 将 P2-05 测试纳入本地 smoke 回归。 |

## Relationship 映射

| Memory 场景 | SpiceDB relationship |
| --- | --- |
| personal memory | `memory:{memory_id}#owner@user:{subject_member_id}` |
| team_shared memory | `memory:{memory_id}#parent_team@team:{team_id}` |
| team_shared + project context | `memory:{memory_id}#parent_project@project:{project_id}` |
| reviewer/curator | `memory:{memory_id}#curator@user:{reviewer_member_id}` |

## 行为

- `MemoryRelationshipService.enqueue_memory_relationships()` 接收 memory dict 和 reviewer member IDs。
- personal memory 缺少 `subject_member_id` 时拒绝入队。
- team_shared memory 缺少 `team_id` 时拒绝入队。
- relationship outbox 使用 P1-11 的稳定 idempotency key；同一组 relationship 重复入队返回同一个 outbox item。
- `InMemoryMemoryService` 仅在注入 `relationship_service` 时写 outbox；未注入时保持 P2-03 CRUD 行为不变。

## 非目标

- 不直接写 SpiceDB。
- 不实现 review queue API。
- 不实现 PostgreSQL outbox 表。
- 不实现 worker 审核通过后的状态机；该能力留给 P2-08 和后续 worker 任务。

## 后续衔接

- P2-06/P2-07：embedding/extraction worker 写入 memory 后可复用该 relationship 服务。
- P2-08：Review Queue API 审核通过时可补写 curator/reviewer relationship。
- P2-20：隔离测试可基于这些 relationship 验证 Alice/Bob 和跨 org memory 隔离。
