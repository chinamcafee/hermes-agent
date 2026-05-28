# GTC-43 Hermes CLI 团队上下文边界需求冻结

日期：2026-05-23

## 范围

本轮仅冻结需求和实现拆解，不修改 CLI 代码。目标是补齐本地 Hermes CLI 对 Team Cloud 个人/团队模式的可见性、连接配置和切换边界。

## 当前缺口

- 本地 CLI 没有 `/team` 命令。
- `/profile` 只表示本地 Hermes profile，不表示 Team Cloud 组织、团队成员。
- CLI 创建 `AIAgent` 时不传 `team_context`。
- Gateway/API Server 已具备团队身份解析和 trusted headers，但普通 CLI 没有对应 UX。
- 用户无法从 prompt 或 status 判断当前是否以团队身份运行。

## 需求决策

1. 新增 `/team` 命令组，负责团队连接和上下文切换。
2. 保持 `/profile` 的本地 profile 语义，不把 profile 伪装成团队帐号。
3. Team Cloud 上下文作为独立 runtime context 注入 `AIAgent`。
4. 普通成员 CLI 不应长期使用 service token；应支持成员 token/PAT/OIDC。
5. CLI 不设计 deployment service token 模式；如果未来出现临时运维凭据，必须与普通成员登录路径隔离并明确提示风险。

## 建议命令

```text
/team status
/team connect <url>
/team token set
/team use <org> <team> [project]
/team off
```

## 验收标准

- 未配置时，`/team status` 显示 `disabled/not connected`。
- 配置后，`/team status` 显示当前 org/team/project/member。
- 团队模式下，`AIAgent.team_context` 非空。
- 本地模式下，`AIAgent.team_context` 为 `None`。
- `/team off` 不删除本地 profile 和普通 config。
- 文档明确说明 local profile 与 Team Cloud team context 是两套概念。
