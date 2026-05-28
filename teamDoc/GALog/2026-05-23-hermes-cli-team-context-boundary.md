# Hermes CLI 团队上下文边界需求日志

日期：2026-05-23

## 背景

用户追问本地 Hermes CLI 如何区分纯本地个人使用和加入 Team Cloud 团队后的团队帐号使用。代码检查显示普通 CLI 尚无专门的团队模式命令，也没有个人/团队切换 UX。

## 事实记录

- `HermesCLI` 创建 `AIAgent` 时传入 `platform="cli"`，未传 `team_context`。
- `/profile` 显示本地 Hermes profile 和 home，不表示 Team Cloud 团队身份。
- `hermes_cli/commands.py` 无 `/team` 命令。
- Gateway 已能通过 Team Cloud identity resolver 解析平台用户并注入 `team_context`。
- API Server 已支持 Team Cloud trusted headers。
- Memory provider 初始化路径已能接收 `team_context`。

## 文档产出

- `teamDoc/18-hermes-cli-team-context-boundary.md`
- `teamDoc/GAStep/09-hermes-cli-team-context-boundary-steps.md`
- `teamDoc/GADoc/GTC-43-hermes-cli-team-context-boundary-requirements.md`
- `teamDoc/GADoc/GTC-44-50-hermes-cli-team-context-backlog.md`
- `teamDoc/GADoc/GTC-43-service-token-bootstrap-boundary.md`

## 结论

本地 Hermes CLI 需要新增一等 `team` 命令组和独立 team context 配置。团队上下文不能与本地 profile 混用；profile 仍表示本地配置隔离，team context 表示 Team Cloud 组织、团队、项目和成员身份。

