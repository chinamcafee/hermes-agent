# P3-13 Retention policies

日期：2026-05-22
状态：Implemented
前置：`P3-11 删除请求`、`P3-12 Hard delete worker`

## 目标

本步骤实现 Team Cloud 数据保留策略 contract：为 session、tool_call、memory、audit_event 定义保留天数和清理动作，生成到期计划，尊重 legal hold，并能在当前 in-memory repositories 上应用策略。真实后台调度、PostgreSQL 分批删除和 Web Console 配置页由后续 P3/P4 工作承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/retention.py` | `RetentionPolicyService`，策略存储、到期规划、应用清理。 |
| `tests/team_cloud/test_retention_policies.py` | 覆盖四类资源、legal hold、应用清理和非法配置。 |
| `teamDoc/GALog/2026-05-22-p3-13-retention-policies.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `retention_policies` domain。 |

## Policy Contract

策略以 `org_id + resource_type` 为 key：

```text
resource_type = session | tool_call | memory | audit_event
retain_for_days > 0
action = archive | soft_delete | hard_delete
```

`plan_retention()` 根据资源时间戳计算 `due_at`，返回：

```text
actions: 到期且可执行的清理动作
skipped: 到期但因 legal_hold 跳过的动作
```

legal hold 可由记录顶层 `legal_hold=true` 或 audit metadata 中 `legal_hold=true` 表达。

## Apply Contract

`apply_retention()` 对当前 in-memory repository 执行动作：

- `session`：`archive/soft_delete` 更新 session status，`hard_delete` 删除 session row。
- `tool_call`：从 session 的 tool_calls 列表删除匹配记录。
- `memory`：`archive` 调用 memory archive，`soft_delete` 调用 memory delete，`hard_delete` 删除 item 和 events。
- `audit_event`：从 audit log 删除匹配事件。

每个应用成功的动作写 `data_retention.applied` audit，metadata 记录 `retain_for_days` 和 `due_at`。

## 非目标

- 不新增 PostgreSQL retention policy 表。
- 不实现 cron/scheduler。
- 不实现批量分页、锁、限速和 dead letter。
- 不提供 Web Console 配置页。
- 不替代 P3-12 删除请求 worker；本步骤只定义常规保留策略。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_retention_policies.py
scripts/run_tests.sh tests/team_cloud/test_retention_policies.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/retention.py tests/team_cloud/test_retention_policies.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/retention.py tests/team_cloud/test_retention_policies.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
