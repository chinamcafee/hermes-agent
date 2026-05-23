# P0-11 风险登记册

日期：2026-05-22
状态：Accepted for P0 execution
前置：`P0-10 GA 验收矩阵`

## 目标

登记进入 P1-P5 前必须持续跟踪的 GA 风险，覆盖 MinIO 许可证、SpiceDB 一致性、pgvector 性能、Hermes core patch、双层记忆隔离、工具权限和备份恢复。

## 工件

| 工件 | 用途 |
| --- | --- |
| [risk-register-v0.csv](artifacts/risk-register-v0.csv) | 风险登记册，后续更新 owner、状态和缓解证据。 |

## 风险汇总

| 类别 | 风险数 | Critical | High | Medium |
| --- | ---: | ---: | ---: | ---: |
| License / Dependency | 2 | 1 | 0 | 1 |
| SupplyChain | 1 | 0 | 1 | 0 |
| Authorization | 2 | 2 | 0 | 0 |
| Memory | 2 | 2 | 0 | 0 |
| Performance | 1 | 0 | 1 | 0 |
| Runtime / Tools | 2 | 1 | 1 | 0 |
| Security | 1 | 1 | 0 | 0 |
| BackupRestore | 1 | 0 | 1 | 0 |

## P0-11 必须跟踪项

1. `RISK-001` MinIO AGPL-3.0：进入 Beta 前必须有法务结论、商业授权或替代路径。
2. `RISK-002` MinIO 镜像发布节奏：P1 compose 可用不等于 GA 可交付，Beta 前必须决定源码自建/受支持发行版。
3. `RISK-003` SpiceDB outbox lag：危险操作在 relationship 未同步时 fail closed。
4. `RISK-005` personal memory 泄漏：任何跨成员召回成功都直接阻断 GA。
5. `RISK-006` team_shared 跨 org 泄漏：pgvector 查询必须先 org/team 过滤，再 SpiceDB check。
6. `RISK-008` Hermes core patch 回归：`team_context` 和工具 hook 必须 feature-gated，不能破坏现有 CLI/gateway。
7. `RISK-009` trusted identity headers spoofing：只有可信 Team Cloud 路径可注入 identity。
8. `RISK-010` 工具权限绕过：拦截点必须覆盖 agent/tool executor，而不仅是 registry dispatcher。

## 风险状态规则

- `Open`：风险已知，尚未完成缓解或验证。
- `Mitigating`：已有 owner 正在实现缓解。
- `Accepted`：非 blocking 风险被正式接受并进入 Post-GA backlog。
- `Closed`：缓解已验证并有证据。

Critical 风险不能以 `Accepted` 状态进入 GA，除非 GA scope 被正式修改并更新 P0-01。

## 与验收矩阵的关系

- `RISK-001` / `RISK-012` 对应 `GA-REL-004` SBOM + license report。
- `RISK-003` / `RISK-004` 对应 `GA-SEC-003`、`GA-BR-002`。
- `RISK-005` / `RISK-006` 对应 `GA-SEC-004`、`GA-SEC-005`。
- `RISK-010` 对应 `GA-SEC-007`。
- `RISK-011` 对应 `GA-BR-005`。

## 后续执行约束

- 每个 P1-P5 work package 若触发 `trigger`，必须更新本登记册。
- `P4-18 Beta exit report` 必须列出所有 Critical/High 风险状态。
- `P5-08 GA sign-off` 之前，Critical 风险必须全部 `Closed`。
- `P5-14 Legal/compliance package` 必须关闭或正式处置 License / Dependency 风险。
