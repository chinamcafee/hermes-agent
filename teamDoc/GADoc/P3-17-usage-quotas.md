# P3-17 Usage/quotas

日期：2026-05-22
状态：Implemented
前置：`P2-18 云会话历史`、`P3-07 MinIO upload/lifecycle`、`P3-16 Audit 高级能力`

## 目标

本步骤实现组织级用量和配额的最小 GA contract：汇总 runs、messages、tokens、tool calls 和 personal backup object size，支持配置组织配额，并在创建 chat run 前对 run quota fail closed。实现保持 in-memory repository contract，后续可替换 PostgreSQL 聚合和计费系统。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/usage.py` | `UsageQuotaService`，负责汇总用量、保存组织配额、评估配额和检查下一次 run。 |
| `team_cloud/api.py` | 新增 usage summary/quota API，并在 `/api/chat/runs` 创建前执行 run quota 检查。 |
| `deploy/team-cloud/web-shell/index.html` | Web Admin 壳新增 Usage tab、用量摘要和配额表单。 |
| `tests/team_cloud/test_usage_quotas.py` | 覆盖用量汇总、配额超限、API 阻断和 Web 控件。 |
| `teamDoc/GALog/2026-05-22-p3-17-usage-quotas.md` | TDD 红绿记录和回归证据。 |

## Usage Contract

`UsageQuotaService.org_summary(org_id)` 返回：

```text
usage.run_count
usage.message_count
usage.token_count
usage.tool_call_count
usage.backup_size_bytes
quotas.run_count
quotas.token_count
quotas.tool_call_count
quotas.backup_size_bytes
quota_status = within_quota | over_quota
violations[]
```

数据来源：

- `run_count`：优先读取 `InMemoryChatRunService` 的 run store；缺省时从 cloud session message/tool call 的 `run_id` 去重推断。
- `message_count` 和 `token_count`：读取 `InMemoryCloudSessionRepository` 的 messages；缺失 token 计为 0。
- `tool_call_count`：读取 cloud session tool calls。
- `backup_size_bytes`：读取 `ObjectManifestService` 中 `object_type=personal_backup`、`status=active` 且 org 匹配的 manifest size。

## API Contract

```text
GET /api/usage/orgs/{org_id}/summary
GET /api/usage/orgs/{org_id}/quotas
PUT /api/usage/orgs/{org_id}/quotas
```

`PUT` 支持非负整数：

```text
run_count
token_count
tool_call_count
backup_size_bytes
actor_member_id
```

`POST /api/chat/runs` 会在 AuthZ 通过后调用 `check_next_run()`。如果下一次 run 会超过组织 `run_count` quota，返回：

```json
{
  "detail": "quota_exceeded",
  "violations": [...]
}
```

状态码为 `429`，不会创建 cloud session 或 run。

## Web Contract

Web Admin 壳新增 `usage` tab，包含：

```text
usage-summary
usage-quota-form
usage-run-count-quota
usage-token-count-quota
usage-tool-call-count-quota
usage-backup-size-bytes-quota
```

Web 端只展示 API 汇总结果并提交配额，不在浏览器端重新计算 usage。

## 非目标

- 不实现计费账单、价格表或成本归集；P4 `Cost/quotas tuning` 承接。
- 不估算单次 prompt 的未来 token 消耗；当前只对 run 数做创建前 fail-closed。
- 不新增 PostgreSQL migration；P3-17 固定 API 和 service contract。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_usage_quotas.py
scripts/run_tests.sh tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/usage.py team_cloud/api.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/usage.py team_cloud/api.py tests/team_cloud/test_usage_quotas.py tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_runtime_event_bridge.py tests/team_cloud/test_backup_storage.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
