# P3-16 Audit 高级能力

日期：2026-05-22
状态：Implemented
前置：`P1-14 Audit 基础能力`、`P3-04 Tool audit`、`P3-15 Permission Explorer GA`

## 目标

本步骤把 P1-14 的最小审计能力提升为 GA 排障和合规可用 contract：支持按 actor、action、resource、decision 和时间范围过滤审计事件，支持按筛选条件导出 JSONL，并提供敏感读取和高危工具两个专项视图。实现继续基于 `InMemoryAuditLog` contract，后续可替换为 PostgreSQL repository，但 API 语义保持稳定。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/audit.py` | 扩展 query filters、敏感读取识别、高危工具识别和 JSONL 导出。 |
| `team_cloud/api.py` | 扩展 `/api/audit/events` 参数，新增 `/api/audit/export`、`/api/audit/sensitive-reads`、`/api/audit/high-risk-tools`。 |
| `deploy/team-cloud/web-shell/index.html` | Web Admin 壳新增 Audit tab、筛选表单、导出按钮和专项视图。 |
| `tests/team_cloud/test_audit_advanced.py` | 覆盖高级过滤、导出脱敏、专项视图和 Web 控件。 |
| `teamDoc/GALog/2026-05-22-p3-16-audit-advanced.md` | TDD 红绿记录和回归证据。 |

## API Contract

`GET /api/audit/events` 支持以下筛选参数：

```text
org_id
action
actor_member_id
actor_type
resource_type
resource_id
decision
created_after
created_before
limit
```

时间参数支持 ISO 8601；没有时区的值按 UTC 处理。查询保持插入顺序，便于 in-memory contract 和现有 P1-14 测试兼容。

`GET /api/audit/export` 使用同一组筛选参数，返回 `application/x-ndjson`。导出会递归脱敏 `api_key`、`token`、`password`、`secret`、`credential` 和 `private_key` 等元数据字段。

`GET /api/audit/sensitive-reads` 返回敏感读取事件。当前识别范围：

- action 为 `memory.read`、`backup.read` 或 `break_glass.accessed`。
- action 以 `.read` 结尾，且 resource type 是 memory/backup/document/personal memory/personal backup。
- audit metadata 标记 `scope=personal/private/break_glass` 或 `sensitivity=restricted/confidential/secret/high`。

`GET /api/audit/high-risk-tools` 返回高危工具事件。当前识别范围：

- action 以 `tool.call.` 开头。
- `cloud_risk_level` 或 `risk_level` 是 `file_write`、`terminal` 或 `destructive`。

## Web Contract

Web Admin 壳新增 `audit` tab，包含：

```text
audit-filter-form
audit-events-table-body
audit-sensitive-reads
audit-high-risk-tools
audit-export-button
```

Web 端只做筛选、展示和下载，不在浏览器端重新判断事件是否敏感或高危。

## 非目标

- 不实现 outbox lag、dead letter 或 permission deny spike 告警；P3-19 承接混沌和告警测试。
- 不引入 PostgreSQL repository；当前固定 API 和 in-memory contract。
- 不实现审计事件分页游标；`limit` 已满足当前 GA foundation smoke。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_audit_advanced.py
scripts/run_tests.sh tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_tool_audit.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/audit.py team_cloud/api.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_tool_audit.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/audit.py team_cloud/api.py tests/team_cloud/test_audit_advanced.py tests/team_cloud/test_audit_baseline.py tests/team_cloud/test_tool_audit.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
