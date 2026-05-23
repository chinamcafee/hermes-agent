# P1-13 组织/团队/成员 API

日期：2026-05-22
状态：Implemented
前置：`P1-12 AuthZ middleware`

## 目标

本步骤实现 Team Cloud 管理 API 的最小可运行切片，覆盖组织创建/list、团队创建/list、成员邀请、成员禁用。成员禁用会同步写入 relationship delete outbox intent，为后续 SpiceDB outbox worker 和 API permission gate 形成闭环。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/admin/organizations.py` | 组织、团队、成员管理服务层和内存 repository。 |
| `team_cloud/admin/__init__.py` | admin primitives 包导出。 |
| `team_cloud/api.py` | 挂载最小组织/团队/成员管理 API。 |
| `tests/team_cloud/test_admin_org_api.py` | API 创建/list/邀请/禁用/outbox/404 测试。 |

## API

- `POST /api/organizations`
- `GET /api/organizations`
- `POST /api/organizations/{org_id}/teams`
- `GET /api/organizations/{org_id}/teams`
- `POST /api/organizations/{org_id}/members/invite`
- `PATCH /api/organizations/{org_id}/members/{member_id}/disable`

## 行为

- 组织以 slug 作为当前内存实现的 stable id。
- 团队隶属于组织。
- 邀请成员创建 `status=invited`。
- 禁用成员设置 `status=suspended`，并写入：
  - operation: `delete`
  - relationship: `organization:{org_id}#member@user:{user_id}`
- 未知组织返回 `404 organization_not_found`。
- 未知成员返回 `404 member_not_found`。

## 非目标

- 不直接连接 PostgreSQL。
- 不实现完整 CRUD update/delete。
- 不实现 invite acceptance workflow。
- 不把 AuthZ middleware 自动套到所有管理 API。
- 不实现 Web 管理页。

## 后续衔接

- P1-14：管理 API 写入 audit events。
- P1-17：Web 成员/团队/角色页调用这些 API。
- P1-19/P1-20：补齐 API 和安全负测。
- 后续 DB repository 替换当前内存 service，保持 API 行为测试不变。
