# P1-12 AuthZ middleware

日期：2026-05-22
状态：Implemented
前置：`P1-09 SpiceDB client`、`P1-11 Relationship outbox`

## 目标

本步骤原实现 Team API 的 FastAPI 权限 gate。Go 服务端追加迁移后，Python `team_cloud/` 中的 middleware 仅作为参考；首次上线应在 `team_cloud_go/` 的 HTTP handler/middleware 中承载同等 fail closed 语义。middleware 按 method/path 匹配规则，将请求主体和资源映射为 SpiceDB check，遇到 deny、SpiceDB error 或 relationship outbox 未 applied 时 fail closed，并生成稳定 permission cache key。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/middleware.py` | route permission rule、AuthZ middleware、cache key。 |
| `team_cloud/authz/__init__.py` | 导出 middleware primitives。 |
| `tests/team_cloud/test_authz_middleware.py` | allow、deny、SpiceDB error、outbox pending、unmatched route 测试。 |

## 行为

- `RoutePermissionRule`：
  - 按 HTTP method 和 path template 匹配。
  - 支持 `{param}` 提取 resource id。
  - 支持 product `action` 或直接 schema `permission`。
- 主体解析：
  - 默认优先读取 `request.state.token_principal`。
  - service account 映射为 `service_account:{id}`。
  - human token 或 JWT principal 映射为 `user:{id}`。
  - 也支持注入 `subject_resolver`，用于测试或网关特殊入口。
- Fail closed：
  - 缺少主体返回 `401 missing_authorization_subject`。
  - resource 缺失返回 `403 missing_authorization_resource`。
  - outbox pending 返回 `403 authorization_pending_relationship_sync`。
  - SpiceDB check 异常返回 `403 authorization_unavailable`。
  - denied 返回 `403 permission_denied`。
- Cache key：
  - 格式：`subject|resource|permission`。
  - 同步写入 `request.state.authz_cache_key`。

## 非目标

- 不把 middleware 自动接入所有 API。
- 不实现 permission cache 存储。
- 不实现 API 管理端点。
- 不实现 permission explain。

## 后续衔接

- P1-13：组织/团队/成员 API 按 route 接入 `RoutePermissionRule`。
- P1-14：deny/error/pending 进入 audit。
- P1-19/P1-20：补齐平台基础与安全负测。
- P3-02：工具策略 hook 复用同一 AuthZ check/fail-closed 语义。
