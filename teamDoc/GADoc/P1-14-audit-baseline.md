# P1-14 Audit 基础能力

日期：2026-05-22
状态：Implemented
前置：`P1-04 PostgreSQL 基础迁移`

## 目标

本步骤实现 Team Cloud 审计能力的最小可运行切片，包含 audit event 服务层、HTTP request 审计 middleware 和查询 API。当前实现使用内存 log 固定行为契约，后续可替换为 PostgreSQL `audit_events` repository。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/audit.py` | `InMemoryAuditLog`、record/query。 |
| `team_cloud/api.py` | `audit_log` 注入、request audit middleware、`/api/audit/events`。 |
| `tests/team_cloud/test_audit_baseline.py` | 记录/过滤、HTTP request 审计、查询 API 测试。 |

## 行为

- `InMemoryAuditLog.record()` 记录：
  - `org_id`
  - `actor_member_id`
  - `actor_type`
  - `action`
  - `resource_type`
  - `resource_id`
  - `decision`
  - `request_id`
  - `metadata`
  - `created_at`
- HTTP middleware：
  - 对非 `/api/audit/events` 请求记录 `http.request`。
  - `status_code < 400` 映射为 `allowed`。
  - `status_code >= 400` 映射为 `error`。
  - metadata 包含 method/path/status_code。
- 查询 API：
  - `GET /api/audit/events`
  - 支持 `org_id`、`action`、`limit`。
  - 查询 API 自身不产生审计事件，避免分页/查看审计时污染结果。

## 非目标

- 不直接连接 PostgreSQL。
- 不实现高级过滤、导出、retention。
- 不实现敏感读视图。
- 不强制所有 domain service 写业务 audit。

## 后续衔接

- P1-13 管理 API 后续可接业务 audit action。
- P1-21 将 audit 计数和错误率纳入观测。
- P3-16 扩展高级 audit filters/export/sensitive read views。
