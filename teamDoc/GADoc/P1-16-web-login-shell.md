# P1-16 Web 登录壳

日期：2026-05-22
状态：Implemented
前置：`P1-03 本地 compose 栈`、`P1-05 Casdoor OIDC 接入`、`P1-13 组织/团队/成员 API`

## 目标

本步骤将 `team-web` 的静态占位页升级为最小可用 Web 登录壳。登录壳负责发起 Casdoor OIDC 登录、处理浏览器回调、保存本地 session、展示当前身份，并在登录后加载组织切换器。

## 工件

| 工件 | 用途 |
| --- | --- |
| `deploy/team-cloud/web-shell/index.html` | 静态 HTML/CSS/JavaScript Web 登录壳。 |
| `tests/team_cloud/test_web_login_shell.py` | OIDC/session/org switcher/操作控件的结构化回归测试。 |

## 行为

- Login view：
  - 默认连接 `http://localhost:8780` Team API。
  - 支持通过 `?api=<base-url>` 覆盖 API base URL。
  - 点击登录后请求 `/auth/oidc/authorize`，并把 `state`、`nonce`、`redirectUri` 写入 `sessionStorage.hermesTeamSession`。
- Callback：
  - 浏览器回到 `/auth/callback?code=...&state=...` 后由静态壳消费参数。
  - 本地校验返回的 `state` 与保存值一致。
  - 调用 `/auth/oidc/callback`，只保存 API 返回的非敏感 `subject/email/name/state`。
- App view：
  - 展示 `session-subject`、email、name。
  - 调用 `/api/organizations` 并渲染 `organization-switcher` 和组织列表。
  - 提供 refresh、logout、error 和 empty state。

## 非目标

- 不保存 access token、refresh token 或 id_token。
- 不实现真实后端 session。
- 不实现 members、teams、roles、permission explorer 页面；这些由 `P1-17` 和 `P1-18` 继续。
- 不新增前端构建系统；P1 仍使用可由 nginx 直接托管的静态壳。

## 后续衔接

- `P1-17`：在登录壳基础上扩展 members、teams、roles 最小管理页。
- `P1-18`：增加权限解释最小页。
- `P2-17`：接入 Web Chat 入口时复用身份和组织上下文。
