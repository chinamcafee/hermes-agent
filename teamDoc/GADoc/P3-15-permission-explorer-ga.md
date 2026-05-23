# P3-15 Permission Explorer GA

日期：2026-05-22
状态：Implemented
前置：`P1-18 权限解释最小页`、`P3-14 Break-glass`

## 目标

本步骤把 P1-18 的最小 Permission Explorer 提升为 GA 可排障 contract：保留原有 SpiceDB check 输入/结果，新增 relationship path、近期 relationship outbox 变更和结构化 deny reason。实现继续复用 `AuthzClient.check()` 作为授权判定真相，relationship outbox 只用于解释路径和排查同步延迟。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/explain.py` | 扩展 `explain_permission()`，返回 `deny_reasons`、`relationship_paths`、`recent_relationship_changes`。 |
| `team_cloud/api.py` | `create_app()` 支持注入 `relationship_outbox_repository` 并传给 explain helper。 |
| `deploy/team-cloud/web-shell/index.html` | Permission tab 展示 deny reason、relationship path、recent changes。 |
| `tests/team_cloud/test_permission_explorer_ga.py` | 覆盖 GA explain payload 和 Web wiring。 |
| `teamDoc/GALog/2026-05-22-p3-15-permission-explorer-ga.md` | TDD 红绿记录和回归证据。 |

## API Contract

`GET /api/authz/explain` 保留 P1 字段：

```text
allowed
reason
subject
resource
permission
cache_key
```

新增 GA 字段：

```text
deny_reasons: string[]
relationship_paths: relationship outbox applied paths matching subject/resource
recent_relationship_changes: latest relationship outbox changes for resource
```

`relationship_paths` 只显示 `status=applied` 且 subject/resource 匹配的 relationship。`recent_relationship_changes` 以资源为边界显示最近 outbox 变更，包含 operation、status、aggregate、created/processed timestamps、attempts 和 last_error。

## Deny Reason

当 `allowed=false` 时，`deny_reasons` 会组合：

- `spicedb_denied`：SpiceDB check 明确 deny。
- `authorization_unavailable` / `authz_client_not_configured`：fail closed。
- `relationship_outbox_pending`：存在 pending/processing/failed 的相关 relationship。
- `relationship_outbox_dead_letter`：存在 dead letter 的相关 relationship。
- `no_applied_relationship_path`：没有已应用的 subject/resource path。

这让管理员能区分模型 deny、同步延迟和 outbox 故障。

## Web Contract

Permission tab 继续展示 decision 详情，并新增三个区块：

```text
permission-deny-reasons
permission-relationship-paths
permission-recent-changes
```

前端只渲染 API 返回内容，不在浏览器端重新推断权限。

## 非目标

- 不调用 SpiceDB expand/explain API。
- 不绘制完整关系图。
- 不实现 audit export；P3-16 承接 Audit 高级能力。
- 不实现 outbox 告警；P3-16/P3-19 承接。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_permission_explorer_minimal.py
scripts/run_tests.sh tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_permission_explorer_minimal.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/ruff check team_cloud/authz/explain.py team_cloud/api.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_permission_explorer_minimal.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m py_compile team_cloud/authz/explain.py team_cloud/api.py tests/team_cloud/test_permission_explorer_ga.py tests/team_cloud/test_permission_explorer_minimal.py tests/team_cloud/test_platform_foundation_suite.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json >/dev/null
scripts/team-cloud-foundation-smoke.sh
```
