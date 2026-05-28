# 2026-05-24 Hermes CLI Team Cloud 一等命令推进日志

## 本次目标

基于 Team Cloud Go 已有 API，在 Hermes CLI 内新增一等团队命令，覆盖服务端连接、成员登录、团队状态查询和 Agent 运行时 `team_context` 注入。

## 完成工作

- 新增 `hermes_cli/team_cloud.py`，封装 Team Cloud CLI client 和命令逻辑。
- 新增 `team_cloud` 默认配置段，保留本地 profile 和 Team Cloud team context 的语义边界。
- 新增 `hermes team` 顶层子命令，支持 `connect/login/status/use/off/logout/token set`。
- 新增 `/team` slash command，支持交互式 CLI 内部团队状态查询和切换。
- CLI、oneshot、TUI、background agent 创建 `AIAgent` 时自动解析并传入 `team_context`。
- Team Cloud Go `/v1/auth/login` 支持 `client=cli`，普通成员可以登录 CLI。
- Team Cloud Go 新增 `/v1/auth/session`，用于 CLI 查询 Bearer session 对应成员身份。
- 更新 `teamDoc/18-hermes-cli-team-context-boundary.md`、GAStep、GADoc、release manual。

## 验证记录

- `venv/bin/python -m pytest -q tests/hermes_cli/test_team_cloud_cli.py`：通过。
- `cd team_cloud && go test ./internal/httpapi -run TestCLIAuthLoginAllowsUserMemberAndSessionIntrospection -count=1`：通过。

## 设计决策

- 普通成员 CLI 使用用户级 session token，不使用 Service token。
- Dashboard 登录面继续限制为 `super_admin/admin`，避免普通成员进入管理后台。
- 第一版 Team Cloud 仍是单团队模型，CLI 的 `team_id` 默认等于 `org_id`，保留后续多团队扩展位。
- `/profile` 保持本地 Hermes profile 语义，团队身份只通过 `/team status` 或 `hermes team status` 展示。

