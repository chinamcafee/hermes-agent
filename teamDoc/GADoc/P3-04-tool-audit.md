# P3-04 Tool audit

日期：2026-05-22
状态：Implemented
前置：`P3-02 TeamToolPolicyHook`, `P3-03 高危工具审批`

## 目标

本步骤为 Team Cloud 工具治理补齐审计落点：把 TeamToolPolicyHook 的 allow、deny、approval 和 error 结果写入 `cloud_tool_calls` 兼容记录，同时写业务 `audit_events`。实现保持可注入，不在 Hermes dispatcher 中硬编码数据库或 Team Cloud client。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/tool_audit.py` | `TeamToolAuditSink`、`cloud_tool_calls` schema 映射、secret redaction。 |
| `team_cloud/tool_policy.py` | 在最终 allow/block 决策处调用可选 audit sink。 |
| `tests/team_cloud/test_tool_audit.py` | 覆盖 approved、denied、secret redaction、risk normalization。 |
| `teamDoc/GALog/2026-05-22-p3-04-tool-audit.md` | TDD 红绿记录和回归证据。 |

## 决策映射

| Policy outcome | `cloud_tool_calls.decision` | Audit action |
| --- | --- | --- |
| SpiceDB allow 且无需审批 | `allowed` | `tool.call.allowed` |
| 高危审批通过 | `approved` | `tool.call.approved` |
| SpiceDB deny / actor missing | `denied` | `tool.call.denied` |
| 用户拒绝审批 | `rejected` | `tool.call.rejected` |
| authz unavailable / approval timeout / audit unavailable | `error` | `tool.call.error` |

## 风险映射

`cloud_tool_calls.risk_level` 沿用 P0 schema 枚举：`safe/network/file_read/file_write/terminal/destructive`。P3-01 的 `file` 会按 permission 转为 `file_read` 或 `file_write`；`secret` 会转为 `destructive`，同时原始 `risk_level=secret` 保留在 audit metadata 中。

## Redaction

`redact_tool_args()` 递归替换 key 包含 `api_key/token/password/passwd/secret/credential/private_key` 的值为 `[REDACTED]`。`input_redacted` 同时进入 cloud tool call 和 audit metadata；原始输入不写入 audit sink。

## 非目标

- 不实现 PostgreSQL repository；P2 的 `InMemoryCloudSessionRepository` 和 P1 的 `InMemoryAuditLog` 已定义行为契约，后续数据库 repository 可替换同一接口。
- 不实现 audit 页面高级过滤；P3-16 承接。
- 不把 audit sink 强制绑定到插件默认路径；企业 runtime 可在具备 cloud session repository/audit repository 后注入。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_tool_audit.py
venv/bin/ruff check team_cloud/tool_audit.py team_cloud/tool_policy.py tests/team_cloud/test_tool_audit.py
venv/bin/python -m py_compile team_cloud/tool_audit.py team_cloud/tool_policy.py tests/team_cloud/test_tool_audit.py
scripts/team-cloud-foundation-smoke.sh
```
