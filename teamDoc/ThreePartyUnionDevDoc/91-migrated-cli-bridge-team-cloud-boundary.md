# 91. 迁移文档：CLI/API Bridge 和 Team Cloud 边界

日期：2026-05-24

来源：原 `hermes-desktop/teamDoc/06-cli-bridge-team-cloud-boundary.md`。

本文件已从 Desktop 文档目录迁移到 Agent 文档目录。原因是 CLI/API Bridge 是 `hermes-agent` 需要提供的稳定契约，Desktop 只消费该契约。

## 决策

`hermes-desktop` 不直连 Team Cloud Go 业务 API。Desktop 只连接 Hermes Agent Runtime Bridge；Team Cloud Go 是 Hermes Agent Runtime Bridge 的上游服务，不是 Desktop 的直接业务依赖。

本文件中的 Hermes Agent Runtime Bridge 包含：

- 本机 `hermes team ...`、`hermes soul ...`、`hermes cloud-backup ...` CLI 命令。
- 本机 Hermes API Server 的 Desktop-friendly team capability 和 chat fast path。
- SSH 模式下的远端 Hermes CLI wrapper。
- remote HTTP 模式下的远端 Hermes API Server bridge endpoint。

## 允许和禁止

允许 Desktop：

- 调用 `hermes team status/connect/login/use/off/logout/breaker --json`。
- 调用 `hermes soul status/show --json`。
- 调用 `hermes cloud-backup status/config/memory/soul --json`。
- 调用 Hermes API Server 的 `/v1/capabilities`、chat endpoint 和未来 bridge endpoint。
- 在用户点击时打开 `<team_cloud_url>/dashboard/`。
- 通过 Hermes Agent 返回的结构化状态展示 Team Cloud URL、成员、角色、熔断、团队父人格版本、effective soul 状态和 Dashboard 入口。

禁止 Desktop：

- 直接调用 Team Cloud Go `/v1/auth/login`、`/v1/auth/session`、`/v1/memory`、`/v1/team-soul`、`/v1/members` 等业务 API 作为主路径。
- 自行保存或解释 Team Cloud session token 明文。
- 自行拼接 org/team/member headers，绕过 Hermes Agent 的 session 验证。
- 复制 Team Cloud Dashboard 的成员管理、团队记忆治理、团队父人格编辑、团队备份恢复和审计页面。

## Bridge 数据流

Local：

```text
Desktop Renderer
  -> Electron IPC
  -> src/main/team-bridge.ts
  -> hermes team/soul/cloud-backup ... --json
  -> 当前本机 Hermes profile
  -> Hermes Agent Team Cloud client
  -> Team Cloud Go
```

SSH：

```text
Desktop Renderer
  -> Electron IPC
  -> src/main/team-bridge.ts
  -> src/main/ssh-remote.ts
  -> 远端 hermes team/soul/cloud-backup ... --json
  -> 远端 Hermes profile
  -> 远端 Hermes Agent Team Cloud client
  -> Team Cloud Go
```

Remote HTTP：

```text
Desktop Renderer
  -> Electron IPC
  -> Hermes API Server bridge endpoint
  -> 远端 Hermes Agent Team Cloud client
  -> Team Cloud Go
```

## Token 和人格边界

- Team Cloud session token 由 Hermes Agent profile 持有，Desktop Renderer 永不接收明文。
- Team parent soul 内容由 Team Cloud Go 权威管理；Desktop 通过 Bridge 只读展示。
- Local soul 内容属于当前 Hermes profile；Desktop 可以继续编辑本地 `SOUL.md`。
- Effective soul 由 Hermes Agent 调用当前 profile 模型供应商合成，Desktop 不自行合成作为运行时依据；模型不可用时 Bridge 返回结构化失败和安全降级组合。

## Chat 运行时

Desktop 聊天是否进入团队模式，必须由 Hermes Agent runtime 决定：

```text
Desktop sendMessage
  -> Hermes API Server 或 CLI fallback
  -> Hermes Agent 解析当前 profile/team session
  -> Team parent soul + local SOUL.md -> effective soul
  -> AIAgent(team_context=...)
  -> TeamMemoryProvider 自动挂载
```

Desktop 不直接调用 Team Cloud `/v1/memory` 或 `/v1/team-soul` 来补写聊天产生的数据。

## 对 hermes-agent 的契约要求

Desktop 需要 Hermes Agent 提供稳定结构化契约：

- `hermes team ... --json`
- `hermes soul ... --json`
- `hermes cloud-backup ... --json`
- `GET /v1/capabilities` 返回 team bridge、team parent soul、effective soul 和 cloud backup capability。
- API Server chat fast path 在团队模式下能由 Hermes Agent 自行解析或验证 team context，并注入 effective soul。

缺少契约时，Desktop 必须降级为 CLI fallback 或显示升级提示，而不是直接绕过 Hermes Agent 调 Team Cloud Go。
