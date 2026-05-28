# 20. Hermes Desktop Team Bridge 集成边界

日期：2026-05-24

## 结论

Hermes Desktop 不应直连 Team Cloud Go 服务端业务 API。符合当前 Hermes Desktop 设计原则的方式是：Desktop 只连接 Hermes Agent Runtime Bridge，由 Hermes Agent CLI/API Server 负责连接 Team Cloud Go、保存成员 session、解析 team context、触发熔断、挂载 `TeamMemoryProvider` 和执行个人记忆备份。

一句话边界：

```text
Hermes Desktop -> Hermes Agent Runtime Bridge -> Team Cloud Go
```

Team Cloud Go 是 Hermes Agent Runtime Bridge 的上游团队服务，不是 Desktop 的直接业务依赖。

## 职责划分

| 组件 | 职责 |
| --- | --- |
| Hermes Desktop | 展示 Team 状态、发起登录/退出/熔断操作、打开 Team Cloud Dashboard、展示聊天团队状态、三段人格和 Cloud Backup UI。 |
| Hermes Agent CLI | `hermes team ...`、`/team ...`、`hermes soul ...`、`/soul ...`、`hermes cloud-backup ...`、`/cloud-backup ...` 的 profile-aware 执行入口，并在 team mode 本地人格保存后调用配置的大模型供应商合并 effective soul。 |
| Hermes Agent API Server | Desktop chat fast path、远程 HTTP 模式 team bridge capability、team context 解析、effective soul 合成和 `AIAgent(team_context=...)` 注入。 |
| Team Cloud Go | 成员、团队记忆、团队父人格、团队级备份、审计、Dashboard、session token 服务端签发与校验。 |
| Team Cloud Dashboard | 首次初始化、团队成员管理、记忆治理、团队父人格治理、备份恢复和审计的唯一管理后台。 |

## Desktop 不直连 Team Cloud Go 的原因

- 避免 Desktop 重复实现 CLI 已经具备的登录、token、profile、熔断和 team context 逻辑。
- 保证 CLI、TUI、oneshot、Gateway、Desktop API fast path 和 CLI fallback 使用同一套团队上下文。
- 降低 Electron Renderer/main process 接触 Team Cloud token 和业务 API 细节的概率。
- 让 Team Cloud Go API 演进只影响 Hermes Agent Bridge 和 Dashboard，不扩散到 Desktop。
- 符合 Desktop 当前“连接 Hermes Agent runtime，而不是重写 runtime 业务客户端”的设计原则。

## Hermes Agent 需要提供的 Bridge 契约

CLI JSON 契约：

```bash
hermes team status --json
hermes team connect <url> --json
hermes team login --org <org> --user <user> --password <password> --json
hermes team use --org <org> --team <team> --project <project> --json
hermes team off --json
hermes team logout --json
hermes team breaker status|open|close|auto --json
hermes soul status|show --json
hermes cloud-backup status|config|memory|soul --json
```

API Server 契约：

- `GET /v1/capabilities` 声明 `team_bridge.enabled`、`team_bridge.api_bridge_contract`、`team_bridge.remote_http_supported`、`team_bridge.team_parent_soul` 和 `cloud_backup.resources`。
- Chat fast path 在团队模式下由 Hermes Agent 自行解析当前 profile 的 `team_cloud` 配置，或验证普通成员 session token 后派生 `team_context`，再合成 effective soul。
- API Server 不要求 Desktop 持有服务级 `X-Hermes-Team-Cloud-Token`。
- API Server 不信任 Desktop 自行传入的 org/team/member headers；团队身份必须来自 Team Cloud session 校验或当前受信 profile。

2026-05-25 状态契约补充：

- `GET /api/team/status` 必须把“已配置 Team Cloud URL”和“已完成成员帐号登录”拆开返回。
- 推荐字段：`connection_configured`、`token_configured`、`account_authenticated`、`login_required`、`saved_context`。
- Desktop 只有在 `account_authenticated=true` 或 `mode=team + context + session无error` 时，才显示 Team mode active。
- 如果只配置了 URL，但未登录或 session 校验失败，Desktop 必须显示 `Team login required`，保留 Dashboard 跳转，但不把聊天和 Persona 入口视为可用团队态。
- 本地 Desktop 优先调用 Hermes Agent API Bridge；若 Bridge 返回“本地态/未登录”但本机 CLI fallback 能读取到同一 profile 的有效 team session，则使用 CLI fallback 的更完整状态，避免旧 API Server 或错误 runtime 造成 CLI/Desktop 状态割裂。

## 三种 Desktop 连接模式

Local：

```text
Desktop -> local hermes team/soul/cloud-backup ... --json -> local Hermes profile -> Team Cloud Go
```

SSH：

```text
Desktop -> ssh remote hermes team/soul/cloud-backup ... --json -> remote Hermes profile -> Team Cloud Go
```

Remote HTTP：

```text
Desktop -> remote Hermes API Server team bridge -> remote Hermes Agent runtime -> Team Cloud Go
```

remote HTTP 模式不能假设本地 CLI 可以代表远端 profile；只有远端 API Server 声明 team bridge capability 时，Desktop 才能启用完整团队功能。

## Token 和安全规则

- Team Cloud session token 由 Hermes Agent profile 保存，Desktop Renderer 永不接收明文。
- Team parent soul 由 Team Cloud Go 权威管理，Desktop 只通过 Hermes Agent Bridge 读取。
- Local soul 仍为当前 Hermes profile 的 `SOUL.md`，Desktop 可以继续编辑。
- Desktop 保存 local soul 时必须走 Hermes Agent Bridge；team mode 下保存成功后由 Hermes Agent 触发 LLM 合并，Desktop 不自行调用模型供应商。
- Desktop main process 不把 token 写入 `desktop.json`、localStorage、日志或崩溃报告。
- 登录密码只作为一次性 IPC 输入传给 Hermes Agent Bridge，不持久化。
- Desktop 可展示 `hasToken`、`member_id`、`role`、`expires_at` 等派生状态。
- Dashboard 管理登录仍只面向 `super_admin/admin`，普通成员 Desktop 不进入服务端管理台。

## Chat 运行时规则

Desktop 发送聊天请求时不直接读写团队记忆 API：

```text
Desktop Chat
  -> Hermes API Server 或 CLI fallback
  -> Team parent soul + local SOUL.md -> effective soul
  -> AIAgent(team_context=...)
  -> TeamMemoryProvider 自动挂载
  -> team_memory_search / team_memory_add / team_memory_propose
```

显式“增加团队记忆”由 Hermes Agent 暴露的 `team_memory_add` 工具写入 Team Cloud Go。非显式 observation 抽取结果由 Hermes Agent runtime 通过事件或文本提示回传 Desktop。Desktop 不直接调用 Team Cloud `/v1/memory` 进行补写。

team mode 下，Desktop 编辑本地人格后的保存流程：

```text
Desktop Local Soul Editor
  -> Hermes Agent Bridge save local SOUL.md
  -> Hermes Agent calls configured model provider
  -> effective soul cache updated or merge_status=failed
  -> Desktop refreshes Effective Soul panel
```

如果模型供应商未配置或不可用，Desktop 应显示“本地人格已保存，但团队父人格合并失败”的非阻塞提示，并展示 Hermes Agent 返回的 `error_code`。本地保存不得回滚，团队父人格不得被本地写入。

## 文档联动

Desktop 侧文档以 `hermes-desktop/teamDoc/ThreePartyUnionDevDoc/README.md` 和 `hermes-desktop/teamDoc/ThreePartyUnionDevDoc/03-desktop-bridge-consumption-contract.md` 为准。原 Desktop `05-agent-cloud-collaboration-topics.md`、`06-cli-bridge-team-cloud-boundary.md` 中涉及 Agent/Team Cloud Go 的内容已迁移到 `teamDoc/ThreePartyUnionDevDoc/90-migrated-desktop-agent-cloud-collaboration-topics.md` 和 `teamDoc/ThreePartyUnionDevDoc/91-migrated-cli-bridge-team-cloud-boundary.md`。Agent 侧本文档固定服务端和 CLI/API Bridge 责任，后续实现或测试变更应同步更新：

- `teamDoc/18-hermes-cli-team-context-boundary.md`
- `teamDoc/17-team-cloud-go-service-design.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/releaseManual/*`
