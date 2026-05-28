# P3-10 组织导出

日期：2026-05-22
状态：Implemented
前置：`P2-18 云会话历史`、`P3-07 MinIO upload/lifecycle`

## 目标

本步骤实现组织级数据导出 snapshot contract：把一个组织的 metadata、sessions/messages/tool_calls、memory_items/memory_events、relationship snapshot 和 audit events 写入本地 `export.zip` 包，并生成 org export manifest。删除请求、真实 MinIO 上传、硬删除 worker 和回灌流程由 P3-11/P3-12/P4 演练承接。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/exports/org.py` | `OrganizationExportService`、JSONL snapshot、secret redaction。 |
| `tests/team_cloud/test_org_export.py` | 覆盖 org scope、manifest counts、relationship snapshot、audit redaction。 |
| `teamDoc/GALog/2026-05-22-p3-10-org-export.md` | TDD 红绿记录和回归证据。 |
| `teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json` | Foundation smoke 新增 `org_export` domain。 |

## Package Contract

`OrganizationExportService.export_org(org_id, actor_member_id)` 输出：

```text
export.zip
  manifest.json
  organizations.jsonl
  members.jsonl
  projects.jsonl
  sessions.jsonl
  messages.jsonl
  tool_calls.jsonl
  memory_items.jsonl
  memory_events.jsonl
  relationships.jsonl
  audit_events.jsonl
```

`projects.jsonl` 当前从 session 和 memory 的 `project_id` 派生，避免在尚无 project repository 的情况下引入新表。后续项目服务落地后可替换为 repository snapshot。

## Scope Rules

- 只导出 `org_id` 匹配的数据。
- `sessions/messages/tool_calls` 通过 `InMemoryCloudSessionRepository` 的 public API 汇总。
- `memory_items/memory_events` 使用 `InMemoryMemoryService` 的 org scope。
- `relationships.jsonl` 从 relationship outbox 中筛选同组织记录，作为 SpiceDB relationship snapshot contract。
- `audit_events.jsonl` 只导出同组织事件。

## Redaction

组织导出不能携带 token、password、secret、credential 或 private key。`OrganizationExportService` 会递归替换 audit metadata 中 key 包含以下片段的值：

```text
api_key, token, password, passwd, secret, credential, private_key
```

替换值固定为 `[REDACTED]`。其他业务字段保持原样。

## 非目标

- 不上传 MinIO org export object。
- 不写 PostgreSQL `object_manifests` / export job repository。
- 不导出附件 blob 内容。
- 不导出 Casdoor 密码、client secret 或 refresh token。
- 不实现删除请求和 hard delete worker。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_org_export.py
scripts/run_tests.sh tests/team_cloud/test_org_export.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/exports tests/team_cloud/test_org_export.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/exports/__init__.py team_cloud/exports/org.py tests/team_cloud/test_org_export.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
