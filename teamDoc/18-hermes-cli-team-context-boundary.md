# Hermes CLI 团队上下文边界需求

日期：2026-05-23

## 背景

当前 `hermes-agent` 已支持 Team Cloud Go 服务端、`/dashboard/` 管理台、Gateway Team identity resolver、API Server trusted team headers，以及 `AIAgent(team_context=...)` 运行时上下文透传。

2026-05-24 起，本地 Hermes CLI 也具备一等 Team Cloud 命令：用户可以在当前 Hermes profile 内连接 Team Cloud、以团队成员帐号登录、查询团队模式状态、选择默认上下文，并在创建 CLI/TUI/oneshot Agent 时自动传入 `team_context`。

## 当前事实

- `hermes_cli/config.py` 新增 `team_cloud` profile-aware 配置段。
- `hermes_cli/team_cloud.py` 提供 Team Cloud HTTP client、登录、状态、上下文解析和命令处理。
- 后续三方联动方案要求新增 `hermes_cli/team_soul.py` 和 `hermes_cli/cloud_backup.py`，用于团队父人格同步、effective soul 展示、本地 memory/soul 云备份。
- `hermes team ...` 是顶层 CLI 子命令，支持 `connect/login/status/use/off/logout/token set`。
- 交互式 CLI 注册 `/team` slash command，支持 `status/connect/login/use/off/logout/token set`。
- CLI、oneshot、TUI 和 background agent 创建 `AIAgent` 时都会尝试解析并传入 `team_context`。
- Team Cloud Go `/v1/auth/login` 支持 `client=cli`，允许普通 `user` 成员登录 CLI；Dashboard 默认登录仍只允许 `super_admin/admin`。
- Team Cloud Go `/v1/auth/session` 用 Bearer session token 返回当前成员会话，CLI `team status` 使用它展示远端成员身份。
- `/profile` 仍只显示本地 Hermes profile 和 home 目录，不代表 Team Cloud 组织、团队或成员身份。
- Gateway 路径已经具备 Team Cloud identity resolver，可将平台用户解析为 `team_context`。
- API Server 路径已经支持可信团队身份 headers，并要求 `X-Hermes-Team-Cloud-Token`。
- Memory provider 初始化路径已经能接收 `team_context`。
- Hermes Desktop 规划为 Hermes Agent Runtime Bridge 的消费者，不直接连接 Team Cloud Go 业务 API。

## 产品目标

Hermes CLI 应具备清晰的个人/团队运行态边界：

- 用户能看到当前是 `local` 还是 `team`。
- 用户能连接 Team Cloud 服务端。
- 用户能选择组织、团队、项目和成员身份。
- 用户能关闭团队上下文，回到纯本地个人模式。
- CLI prompt、`/status`、`/profile` 或新增 `/team status` 能显示当前团队上下文。
- 团队上下文只影响 Team Cloud 相关能力，不应破坏本地 profile、模型配置、工具配置和普通个人记忆。

## 推荐命令

| 命令 | 类型 | 职责 |
| --- | --- | --- |
| `/team status` | slash command | 显示当前 Team Cloud URL、org/team/project/member、远端状态和熔断状态。 |
| `/team connect <url>` | slash command | 设置当前 profile 的 Team Cloud 服务地址。 |
| `/team login <org> <user> [team] [project]` | slash command | 用成员帐号密码登录 Team Cloud，保存 session token。 |
| `/team token set <token>` | slash command | 手工写入 Team Cloud session token，主要用于调试或自动化。 |
| `/team use <org> <team> [project]` | slash command | 将当前 CLI 会话切换到指定团队上下文。 |
| `/team off` | slash command | 当前会话关闭团队上下文，回到本地个人模式。 |
| `/team logout` | slash command | 删除本地 Team Cloud session token 并关闭团队模式。 |
| `hermes team status` | CLI subcommand | 非交互查看团队连接和当前上下文。 |
| `hermes team connect <url>` | CLI subcommand | 非交互配置 Team Cloud URL。 |
| `hermes team login --org <org> --user <user>` | CLI subcommand | 登录成员帐号，写入当前 profile `.env`。 |
| `hermes team use ...` | CLI subcommand | 非交互设置默认团队上下文。 |
| `hermes team off/logout` | CLI subcommand | 关闭团队模式或删除本地 token。 |
| `/soul status` | slash command | local mode 显示本地人格；team mode 显示团队父人格、本地人格和合并后人格状态。 |
| `/soul show team\|local\|effective` | slash command | 查看团队父人格、本地人格或合并后人格内容。 |
| `/soul merge` | slash command | team mode 下使用当前 Hermes 模型供应商重新合并团队父人格和本地人格；local mode 返回无需合并。 |
| `/cloud-backup status` | slash command | 查看共用 MinIO/S3-compatible 配置和 memory/soul 两类资源备份状态。 |
| `/cloud-backup config ...` | slash command | 配置用户自有 MinIO/S3-compatible endpoint、bucket、root prefix 和 access/secret env key。 |
| `/cloud-backup memory schedule <cadence>` | slash command | 设置本地个人记忆备份周期，创建 Hermes cron no-agent job。 |
| `/cloud-backup memory backup/history/restore` | slash command | 立即备份、列出和恢复当前 Hermes profile 的 `memories/` 文件。 |
| `/cloud-backup soul schedule <cadence>` | slash command | 设置本地 `SOUL.md` 备份周期，创建 Hermes cron no-agent job。 |
| `/cloud-backup soul backup/history/restore` | slash command | 立即备份、列出和恢复当前 Hermes profile 的 `SOUL.md`。 |

## 配置建议

新增 profile-aware 配置段，存储在当前 Hermes profile 的 `config.yaml`：

```yaml
team_cloud:
  enabled: false
  url: ""
  default_org_id: ""
  default_team_id: ""
  default_project_id: ""
  default_member_id: ""
  token_env: HERMES_TEAM_CLOUD_SESSION_TOKEN
  circuit_breaker:
    mode: auto
    state: closed
```

敏感 session token 不写入 `config.yaml`，进入当前 Hermes profile 的 `.env`：

```bash
HERMES_TEAM_CLOUD_SESSION_TOKEN=hcs_...
```

## 运行时规则

1. CLI 默认是本地个人模式。
2. 只有 `team_cloud.enabled=true` 且 URL、token、org/team/member 均有效时，CLI 才构造 `team_context`。
3. `team_context` 传入 CLI/TUI/oneshot/background `AIAgent`，并继续透传给 memory provider、tool policy hook、runtime event bridge。
4. `/team off` 只关闭团队上下文，不修改本地 Hermes profile。
5. `/team logout` 删除 `HERMES_TEAM_CLOUD_SESSION_TOKEN` 并关闭本地团队模式。
6. `/profile` 保持本地 profile 语义；团队身份由 `/team status` 显示。
7. CLI 状态栏在团队模式下常驻显示 Team 身份；Team Cloud API 熔断时显示 paused。
8. `/team breaker status|open|close|auto` 可查看、手动打开、手动关闭或恢复自动熔断。

## Team Parent Soul 和 Hermes Desktop Bridge 边界

2026-05-24 补充：

- Hermes Desktop 不直接调用 Team Cloud Go `/v1/auth/login`、`/v1/auth/session`、`/v1/memory`、成员管理或备份恢复 API 作为主路径。
- Desktop local 模式应调用本机 `hermes team ... --json`、`hermes soul ... --json` 和 `hermes cloud-backup ... --json`。
- Desktop ssh 模式应调用远端 `hermes team ... --json`、`hermes soul ... --json` 和 `hermes cloud-backup ... --json`，配置落到远端 Hermes profile。
- Desktop remote HTTP 模式应调用远端 Hermes API Server team bridge endpoint；未声明 capability 时只能降级提示或打开 Team Cloud Dashboard。
- Desktop Renderer 不应接收 Team Cloud session token 明文；CLI/API Bridge 只返回 `hasToken`、member、role、context、expires、breaker 等派生状态。
- Chat fast path 是否进入团队模式必须由 Hermes Agent 解析或验证 team context 后决定，Desktop 不自行拼接 org/team/member headers。
- team mode 下，Hermes Agent 必须同步 Team Cloud Go 的团队父人格，并与本地 `SOUL.md` 合成 effective soul；冲突时以团队父人格为准。
- CLI 和 Desktop 都不能保存团队父人格；但 team mode 下保存、恢复或重置本地 `SOUL.md` 后，Hermes Agent 必须调用当前 profile 配置的大模型供应商合并团队父人格和本地人格。
- 未配置模型供应商或供应商不可用时，本地人格保存仍成功，CLI/Desktop 必须显示优雅失败提示，并使用安全降级组合保证团队父人格仍优先。

因此 CLI 的 JSON 输出是 Desktop 集成的主要稳定契约。所有人类可读文本可以继续优化，但 Desktop 只能依赖结构化字段。

## Team Cloud 记忆运行时

2026-05-24 补充：

- CLI team mode 下，`AIAgent` 会自动挂载 first-party `TeamMemoryProvider`，不要求用户额外安装 `plugins/memory/team_cloud`。
- 显式“增加团队记忆”“保存为团队记忆”等自然语言请求必须调用 `team_memory_add`。该工具写入 Team Cloud Go `POST /v1/memory`，创建 `scope=team_shared`、`status=active`、`source_type=admin_created` 的记忆。
- `team_memory_propose` 只用于“提交审核候选”，服务端默认进入 `pending_review`，需要 Dashboard 待审队列批准后才会进入 active 召回。
- 每个完整 turn 结束后，provider 会调用 `/v1/memory/observations` 写入 observation。observation 不是已生效记忆；当前 Go 服务端会保存为 `pending`，自动生成可见记忆需要后续 extraction worker/离线任务消费。
- 每个 turn 开始前，provider 会调用 `/v1/memory/prefetch` 查询 `team_shared` 记忆，并把结果注入 `<memory-context>`；个人记忆继续由本地 Hermes 记忆系统处理。
- 当 provider 收到 observation 抽取结果时，CLI 会打印 `团队记忆已抽取：<id> - <content>`，让用户知道本轮自动抽取了什么团队记忆。

## 安全边界

- Team Cloud Go Dashboard bootstrap 已取消部署级 service token；普通成员 CLI 不应设计 service token 模式。
- 普通成员 CLI 使用 Team Cloud Go `client=cli` 登录，服务端签发 Redis-backed opaque session token。
- Dashboard 登录面仍只允许 `super_admin/admin`，避免普通成员进入管理台。
- 团队上下文必须由 Team Cloud 服务端登录和 `/v1/auth/session` 验证，不能仅信任本地用户填写的 org/team/member。
- Team Cloud CLI provider 不暴露云端 personal memory 写入或备份工具；个人记忆和本地人格备份只能走 `/cloud-backup memory|soul ...`。

## 交付验收

- `hermes` 本地启动默认显示本地个人模式。
- `/team status` 在未配置时显示 `mode: local`。
- `/team connect`、`/team login` 后，新建 `AIAgent` 能收到完整 `team_context`。
- `/team off` 后，新建会话不再传入 `team_context`。
- 团队模式下 `team_memory_search` 请求包含 org/team/member/project，并显式 `include_personal=false`。
- 团队模式下显式“增加团队记忆”会暴露并使用 `team_memory_add`，而不是本地 `memory` 工具。
- 团队模式下保存本地人格后会触发 LLM effective soul 合并；合并失败时返回结构化错误，不回滚本地 `SOUL.md`。
- 非显式创建但服务端返回抽取结果时，CLI 输出团队记忆 id 和内容。
- 文档明确区分本地 profile 与 Team Cloud team context。
