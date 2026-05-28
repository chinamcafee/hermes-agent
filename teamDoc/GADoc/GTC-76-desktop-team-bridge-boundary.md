# GTC-76 Desktop Team Bridge 边界确认

日期：2026-05-24

## 需求

用户确认 Hermes Desktop 原则上不直连 Team Cloud Go，而是由 Hermes CLI/API Server 连接 Team Cloud 并向 Desktop 暴露本地或远程 Bridge 能力。需要判断该职责拆分是否符合 Desktop 当前设计原则，并同步完善 `hermes-agent` 与 `hermes-desktop` 双侧文档。

## 结论

该职责拆分符合现有设计。

`hermes-desktop` 当前是 Hermes Agent runtime 的桌面外壳，负责安装、连接、配置和操作 Hermes Agent，而不是重写 Hermes runtime 或 Team Cloud Go 客户端。因此团队模式应保持：

```text
Hermes Desktop -> Hermes Agent Runtime Bridge -> Team Cloud Go
```

Desktop 可以展示团队状态、发起登录、控制熔断、打开 Dashboard 和展示团队聊天状态；但 Team Cloud Go 业务 API、session token、team context、团队记忆写入和权限边界由 Hermes Agent Bridge 与 Team Cloud Go 共同承担。

## 文档落点

- `teamDoc/20-desktop-team-bridge-boundary.md`
- `teamDoc/18-hermes-cli-team-context-boundary.md`
- `teamDoc/17-team-cloud-go-service-design.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/releaseManual/team-cloud-ga-release-manual.md`
- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `../hermes-desktop/teamDoc/ThreePartyUnionDevDoc/03-desktop-bridge-consumption-contract.md`
- `../hermes-desktop/teamDoc/README.md`
- `../hermes-desktop/teamDoc/01-current-state-audit.md`
- `../hermes-desktop/teamDoc/02-conflict-matrix.md`
- `../hermes-desktop/teamDoc/03-desktop-team-mode-architecture.md`
- `../hermes-desktop/teamDoc/04-implementation-roadmap.md`
- `teamDoc/ThreePartyUnionDevDoc/90-migrated-desktop-agent-cloud-collaboration-topics.md`
- `teamDoc/ThreePartyUnionDevDoc/91-migrated-cli-bridge-team-cloud-boundary.md`

## 后续实现要求

- Hermes Agent CLI 命令需要稳定 `--json` 输出，供 Desktop main process 解析。
- Hermes API Server 需要声明 team bridge capability，服务 remote HTTP 模式。
- Desktop main process 推荐新增 `team-bridge.ts`，禁止以 Team Cloud Go 业务 API 为主路径。
- Desktop Renderer 不接收 Team Cloud session token 明文。
