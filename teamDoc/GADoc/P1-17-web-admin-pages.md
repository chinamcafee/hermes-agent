# P1-17 Web 成员/团队/角色页

日期：2026-05-22
状态：Implemented
前置：`P1-13 组织/团队/成员 API`、`P1-16 Web 登录壳`

## 目标

本步骤在 P1-16 静态登录壳上增加组织作用域的最小管理界面，覆盖 teams、members、roles 三个页面。页面提供团队创建/list、成员邀请/list/禁用、角色展示，以及每个面板的 empty/error 状态。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/web-shell/index.html` | 静态 Web 管理界面，包含 teams/members/roles tabs。 |
| `team_cloud/admin/organizations.py` | 补齐 `list_members()`，支撑成员列表页。 |
| `team_cloud/api.py` | 新增 `GET /api/organizations/{org_id}/members`。 |
| `tests/team_cloud/test_web_admin_pages.py` | 成员列表 API、Web 面板结构和 API wiring 测试。 |

## 行为

- Teams：
  - `GET /api/organizations/{org_id}/teams` 加载列表。
  - `POST /api/organizations/{org_id}/teams` 创建团队。
  - 空列表展示 empty state。
- Members：
  - `GET /api/organizations/{org_id}/members` 加载成员列表。
  - `POST /api/organizations/{org_id}/members/invite` 邀请成员。
  - `PATCH /api/organizations/{org_id}/members/{member_id}/disable` 禁用成员。
  - suspended 成员禁用按钮不可用。
- Roles：
  - 展示 owner/admin/security_admin/member/guest 的最小角色矩阵。
  - 角色来源对齐 P0-07 SpiceDB schema v0；本阶段只展示，不编辑。
- Error state：
  - 全局登录/组织错误走 `shell-error`。
  - teams/members/roles 面板各自保留独立错误容器。

## 非目标

- 不实现角色编辑或 SpiceDB relationship 写入 UI。
- 不实现成员 remove、invite accept、团队 disable。
- 不引入前端构建系统。
- 不实现 permission explorer；该范围由 `P1-18` 承接。

## 后续衔接

- `P1-18`：在现有 tabs 基础上增加权限解释最小页。
- `P1-19/P1-20`：补齐平台基础测试和安全负测。
- `P3-15/P3-22`：权限浏览器 GA 和 Admin UX 收尾。
