# P1-18 权限解释最小页

日期：2026-05-22
状态：Implemented
前置：`P1-09 SpiceDB client`、`P1-12 AuthZ middleware`、`P1-17 Web 成员/团队/角色页`

## 目标

本步骤实现最小 Permission Explorer：管理员可以输入 subject、resource、action 或 schema permission，查看当前 check 判定、原因和 permission cache key。该功能用于 P1 阶段调试权限 gate，不承担完整关系路径解释。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/explain.py` | permission explain helper，封装 check、fail-closed 和 payload。 |
| `team_cloud/api.py` | 新增 `GET /api/authz/explain`，支持注入 `authz_client`。 |
| `team_cloud/authz/__init__.py` | 导出 `explain_permission()`。 |
| `deploy/team-cloud/web-shell/index.html` | 新增 Permission tab、表单和结果渲染。 |
| `tests/team_cloud/test_permission_explorer_minimal.py` | explain API、fail-closed、Web wiring 测试。 |

## API

`GET /api/authz/explain`

Query：

- `subject_type`: `user` 或 `service_account`。
- `subject_id`: subject id。
- `resource_type`: SpiceDB resource type。
- `resource_id`: resource id。
- `permission`: schema permission，可选。
- `action`: 产品动作名，可选；当 `permission` 为空时解析为 schema permission。

Response：

- `allowed`: bool。
- `reason`: `allowed`、`denied`、`authorization_unavailable` 或 `authz_client_not_configured`。
- `subject`: `type:id`。
- `resource`: `type:id`。
- `permission`: 实际检查的 schema permission。
- `cache_key`: 与 P1-12 middleware 一致的 `subject|resource|permission`。

## 行为

- 当 `authz_client` 已注入时，调用同一 `check()` 契约。
- 当 `authz_client` 未配置时，返回 fail-closed deny，reason 为 `authz_client_not_configured`。
- 当 check 抛出异常时，返回 fail-closed deny，reason 为 `authorization_unavailable`。
- Web 端 Permission tab 调用 `/api/authz/explain` 并展示判定、原因、subject、resource、permission 和 cache key。

## 非目标

- 不实现 SpiceDB explain/expand 路径。
- 不展示 relationship graph。
- 不写 audit event。
- 不实现 break-glass 或临时授权。

## 后续衔接

- `P1-19/P1-20`：加入平台测试和安全负测。
- `P3-15`：升级为 Permission Explorer GA，补关系路径、近期变更和 deny reason。
