# P3-19 AuthZ chaos tests

日期：2026-05-22
状态：Implemented
前置：`P3-02 TeamToolPolicyHook`、`P1-11 Relationship outbox`、`P1-12 AuthZ middleware`、`P3-15 Permission Explorer GA`

## 目标

本步骤把 AuthZ fail-closed 从单点负测扩展为 chaos contract：当 SpiceDB 不可用、relationship outbox 滞后或进入 dead letter 时，管理 API、chat run 和高危工具必须拒绝执行，并输出可诊断的拒绝原因，避免把基础设施故障误判成普通权限 deny。

## 工件

| 工件 | 用途 |
| --- | --- |
| `tests/team_cloud/test_authz_chaos.py` | 覆盖 SpiceDB outage、outbox lag、dead letter fail-closed。 |
| `team_cloud/authz/middleware.py` | 将 `spicedb_error` fail-closed 决策映射为 `authorization_unavailable`。 |
| `team_cloud/api.py` | Chat run 权限检查将 `spicedb_error` 映射为 `authorization_unavailable`。 |
| `team_cloud/authz/outbox.py` | 新增 `fail_closed_status()`，输出 pending lag/dead letter 证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | 新增 `authz_chaos` smoke domain。 |
| `scripts/team-cloud-foundation-smoke.sh` | foundation smoke 纳入 P3-19 chaos 测试。 |

## Chaos Contract

```text
SpiceDB outage
  -> SpiceDBClient fail-closed 返回 reason=spicedb_error
  -> API middleware/chat run 返回 403 authorization_unavailable
  -> 高危工具 policy block，metadata.reason=authorization_unavailable

Outbox lag/dead letter
  -> RelationshipOutboxService.fail_closed_status() 返回 blocked=true
  -> pending/processing/failed 可标记 relationship_outbox_pending
  -> 超过 lag_after 的未完成项额外标记 relationship_outbox_lag
  -> dead_letter 标记 relationship_outbox_dead_letter
  -> 相关资源在 outbox 未 applied 前跳过 AuthZ allow 检查并 fail closed
```

## 非目标

- 不引入真实 SpiceDB/网络故障注入；P4 `Chaos drills` 会覆盖外部依赖级别演练。
- 不改变 relationship outbox worker 的重试/投递语义。
- 不改变普通权限 deny 的返回语义，普通 deny 仍返回 `permission_denied`。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py
scripts/run_tests.sh tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/authz/middleware.py team_cloud/authz/outbox.py team_cloud/api.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/authz/middleware.py team_cloud/authz/outbox.py team_cloud/api.py tests/team_cloud/test_authz_chaos.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_relationship_outbox.py tests/team_cloud/test_team_tool_policy_hook.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_platform_security_negative.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
