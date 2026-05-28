# P5-05 API 文档

日期：2026-05-23
状态：Implemented
前置：`P5-04 管理员和用户手册`

## 目标

本步骤固定 Team API、Memory API 和 AuthZ API 的 GA 文档 contract，并把 Chat/Session、Backup Policy、Audit、Usage 和 Notification API 纳入同一个 release artifact。文档只记录当前 `team_cloud/api.py` 已实现并由测试覆盖的接口。

> 2026-05-24 GTC-77 更新：本文件属于 Python `team_cloud/` 历史 API artifact。Team Cloud Go 首发 GA 后，成员个人备份 policy API 不再作为主路径；本地 memory/soul 备份由 Hermes CLI `/cloud-backup memory|soul` 管理，团队父人格和团队备份 API 以 `teamDoc/ThreePartyUnionDevDoc/04-team-cloud-go-soul-api-dashboard-backup-plan.md` 为准。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/api_docs.py` | `build_api_docs_package()` 生成 API docs JSON contract。 |
| `scripts/team-cloud-api-docs.py` | 写出 API docs JSON artifact。 |
| `teamDoc/GADoc/artifacts/release/team-cloud-api-docs-v0.json` | P5-05 API 文档 artifact。 |
| `tests/team_cloud/test_api_docs_package.py` | P5-05 contract 测试。 |

## Auth

- Identity provider：Casdoor。
- 用户调用：Casdoor JWT。
- 自动化调用：scoped PAT 或 service account token。
- 授权边界：受保护 Team API 通过 SpiceDB fail-closed check。

## Team API

关键入口：`POST /api/chat/runs`。

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/healthz` | 进程健康。 |
| `GET` | `/readyz` | 配置和 migration readiness。 |
| `GET` | `/metrics` | Prometheus metrics。 |
| `GET` | `/auth/oidc/authorize` | 生成 Casdoor OIDC authorize URL。 |
| `GET` | `/auth/oidc/callback` | 交换 code 并校验 ID token。 |
| `GET` | `/api/whoami` | 返回 JWT principal。 |
| `POST` | `/api/organizations` | 创建组织。 |
| `GET` | `/api/organizations` | 列出组织。 |
| `GET` | `/api/organizations/{org_id}/members` | 列出成员。 |
| `POST` | `/api/organizations/{org_id}/members/invite` | 邀请成员。 |
| `PATCH` | `/api/organizations/{org_id}/members/{member_id}/disable` | 禁用成员并写 relationship delete outbox intent。 |
| `POST` | `/api/chat/runs` | 创建团队上下文 chat run。 |
| `GET` | `/api/chat/runs/{run_id}/events` | 读取 chat run events。 |
| `GET` | `/api/cloud/sessions` | 按 org/project/member/q 查询 cloud sessions。 |
| `GET` | `/api/cloud/sessions/{session_id}` | 获取 session history。 |
| `POST` | `/api/cloud/sessions/{session_id}/tool-calls` | 写入 tool call history。 |
| `POST` | `/api/runtime/events` | 摄取 runtime events。 |

## Memory API

关键入口：`POST /v1/memory/prefetch`。

| Method | Path | 说明 |
| --- | --- | --- |
| `POST` | `/v1/memory` | 创建 personal 或 team_shared memory。 |
| `GET` | `/v1/memory` | 按 org、scope、status、type、sensitivity 查询记忆。 |
| `PATCH` | `/v1/memory/{memory_id}` | 更新内容并提升 version。 |
| `POST` | `/v1/memory/{memory_id}/archive` | 归档记忆。 |
| `DELETE` | `/v1/memory/{memory_id}` | 软删除记忆。 |
| `POST` | `/v1/memory/{memory_id}/restore` | 恢复记忆。 |
| `POST` | `/v1/memory/observations` | 写入 runtime observation。 |
| `POST` | `/v1/memory/prefetch` | 执行双层记忆召回。 |

## Memory Review API

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/v1/memory/review` | 列出 pending review items。 |
| `POST` | `/v1/memory/review/{review_id}/approve` | 批准候选记忆，可带 edits。 |
| `POST` | `/v1/memory/review/{review_id}/reject` | 拒绝候选记忆并记录 reason。 |

## AuthZ API

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/authz/explain` | 解释 subject/resource/action 或 permission 的授权决策。 |

## Backup Policy API

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/v1/me/memory-backup-policy` | 历史 Python API：读取成员个人记忆备份策略；Go GA 主路径不再使用。 |
| `PUT` | `/v1/me/memory-backup-policy` | 历史 Python API：更新 cadence、retention、encryption 和 notification channels；Go GA 主路径不再使用。 |

## Audit、Usage 和 Notification API

| Method | Path | 说明 |
| --- | --- | --- |
| `GET` | `/api/usage/orgs/{org_id}/summary` | 读取组织用量摘要。 |
| `GET` | `/api/usage/orgs/{org_id}/quotas` | 读取组织配额。 |
| `PUT` | `/api/usage/orgs/{org_id}/quotas` | 更新组织配额。 |
| `GET` | `/api/notifications` | 查询通知。 |
| `POST` | `/api/notifications/{notification_id}/ack` | 确认通知。 |
| `GET` | `/api/audit/events` | 查询审计事件。 |
| `GET` | `/api/audit/sensitive-reads` | 查询敏感读取视图。 |
| `GET` | `/api/audit/high-risk-tools` | 查询高危工具视图。 |
| `GET` | `/api/audit/export` | 导出 JSONL 审计事件。 |

## Examples

### curl_create_org

```bash
curl -X POST "$TEAM_CLOUD_URL/api/organizations" \
  -H "Authorization: Bearer $TEAM_CLOUD_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"slug":"acme","name":"Acme"}'
```

### python_prefetch_memory

```python
client.post(
    "/v1/memory/prefetch",
    json={
        "org_id": "org-1",
        "member_id": "alice",
        "team_id": "team-1",
        "query": "roadmap",
    },
)
```

### service_account_chat_run

```bash
curl -X POST "$TEAM_CLOUD_URL/api/chat/runs" \
  -H "Authorization: Bearer $SERVICE_ACCOUNT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @run.json
```

## Error Model

| Status | detail |
| --- | --- |
| `400` | `invalid_request` 或 `<field>_required`。 |
| `401` | `missing_principal`。 |
| `403` | `permission_denied` 或 `authorization_unavailable`。 |
| `404` | `resource_not_found`。 |
| `409` | review item state conflict。 |
| `429` | `quota_exceeded`。 |

## 运行

```bash
scripts/team-cloud-api-docs.py --output teamDoc/GADoc/artifacts/release/team-cloud-api-docs-v0.json
```

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_api_docs_package.py
scripts/run_tests.sh tests/team_cloud/test_api_docs_package.py tests/team_cloud/test_admin_org_api.py tests/team_cloud/test_memory_crud_api.py tests/team_cloud/test_memory_prefetch_pipeline.py tests/team_cloud/test_authz_middleware.py tests/team_cloud/test_cloud_session_history.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/api_docs.py scripts/team-cloud-api-docs.py tests/team_cloud/test_api_docs_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/api_docs.py scripts/team-cloud-api-docs.py tests/team_cloud/test_api_docs_package.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-api-docs-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
