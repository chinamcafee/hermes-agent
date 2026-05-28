# GTC-44 到 GTC-50 Hermes CLI 团队模式 Backlog

日期：2026-05-23
更新：2026-05-24，GTC-44 到 GTC-50 已完成实现和验证。

## 目标

将本地 Hermes CLI 从“只能个人本地运行”扩展为“可显式连接 Team Cloud 并携带团队上下文运行”，同时保留纯本地个人模式。

## Backlog

| ID | 标题 | 验收摘要 |
| --- | --- | --- |
| GTC-44 | CLI team config schema | Done：`team_cloud` 配置可加载，token 不进入 config.yaml。 |
| GTC-45 | `/team` slash command registry | Done：`/team status/connect/login/token/use/off/logout` 可用并出现在 help/autocomplete。 |
| GTC-46 | CLI `team_context` 注入 | Done：CLI/TUI/oneshot/background 团队模式下创建 `AIAgent(team_context=...)`。 |
| GTC-47 | prompt/status UX | Done：`hermes team status` 和 `/team status` 显示 local/team 模式。 |
| GTC-48 | Team Cloud 身份验证闭环 | Done：CLI 登录和 session introspection 经 Team Cloud 验证。 |
| GTC-49 | 文档和 release manual 更新 | Done：使用手册覆盖 local/team 切换、token 类型和故障处理。 |
| GTC-50 | CLI 团队模式 GA 验证 | Done：Python 单元测试、Go API 测试、memory provider 注入测试通过。 |

## 非目标

- 不把 Team Cloud 管理台迁回本地 Hermes dashboard。
- 不把本地 Hermes profile 改名为团队帐号。
- 不让普通成员长期使用 bootstrap service token 作为个人登录方式。

## 完成摘要

- 新增 `hermes_cli/team_cloud.py`，集中处理 Team Cloud URL、成员登录、session token、status 和 `team_context`。
- 新增 profile-aware `team_cloud` 配置段；敏感 token 写入 `.env` 的 `HERMES_TEAM_CLOUD_SESSION_TOKEN`。
- 新增 `hermes team` 顶层子命令和交互式 `/team` slash command。
- CLI、TUI、oneshot 和 background agent 均会在配置完整时传入 `team_context`。
- Team Cloud Go `/v1/auth/login` 支持 `client=cli`，普通用户可登录 CLI；Dashboard 管理页仍限制 `super_admin/admin`。
- Team Cloud Go 新增 `/v1/auth/session`，供 CLI 查询当前 Bearer session 对应的成员身份。
