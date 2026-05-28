# Hermes CLI 团队上下文边界实现计划

日期：2026-05-23

## 目标

为本地 Hermes CLI 增加明确的个人/团队运行态边界，让用户能从 CLI 内连接 Team Cloud、查看团队身份、切换团队上下文并回到纯本地模式。

本文件记录新增需求和实施拆解。2026-05-24 已完成 Hermes CLI 一等 Team Cloud 命令、Go 后端 CLI 登录补齐、文档和验证闭环。

## 工作包

| ID | 工作包 | 主要产出 | 前置 | 状态 |
| --- | --- | --- | --- | --- |
| GTC-43 | CLI 团队边界需求冻结 | 需求文档、步骤、进度和日志 | GTC-42 | Done |
| GTC-44 | CLI team config schema | `team_cloud` config 段、secret/env 读取规则、测试 | GTC-43 | Done |
| GTC-45 | `/team` slash command registry | `/team status/connect/login/token/use/off/logout` 命令和 help/autocomplete | GTC-44 | Done |
| GTC-46 | CLI `team_context` 注入 | 本地 CLI/TUI/oneshot/background 创建 `AIAgent` 时按配置传入 `team_context` | GTC-45 | Done |
| GTC-47 | prompt/status UX | `/team status` 显示个人/团队模式和远端会话 | GTC-46 | Done |
| GTC-48 | Team Cloud 身份验证闭环 | CLI 调 Team Cloud 登录和 session introspection，避免本地伪造 | GTC-46 | Done |
| GTC-49 | 文档和 release manual 更新 | CLI 使用手册、管理员手册、minikube 连接手册 | GTC-48 | Done |
| GTC-50 | CLI 团队模式 GA 验证 | 单元测试、Go API 测试、memory provider 注入验证 | GTC-49 | Done |
| GTC-68 | Team Cloud 记忆运行时自动挂载 | Team Cloud 模式下自动启用 TeamMemoryProvider，显式团队记忆写入 Team API | GTC-50 | Done |

## GTC-43：CLI 团队边界需求冻结

- [x] 记录当前 CLI 无 `/team` 命令、无本地团队上下文状态。
- [x] 记录 Gateway/API Server 已支持 `team_context`，CLI 需要补一等 UX。
- [x] 定义 `/team status/connect/token/use/off` 命令建议。
- [x] 定义 profile-aware `team_cloud` 配置和 token secret 边界。
- [x] 写入 progress tracker。

## GTC-44：CLI team config schema

- [x] 在 `hermes_cli/config.py` 新增 `team_cloud` 配置段。
- [x] token 从 `.env` 读取，不进入 `config.yaml`。
- [x] 增加配置加载测试。

## GTC-45：`/team` slash command registry

- [x] 在 `hermes_cli/commands.py` 增加 `CommandDef("team", ...)`。
- [x] 在 `HermesCLI.process_command()` 增加 `/team` 分发。
- [x] 支持 `status`、`connect`、`login`、`token set`、`use`、`off`、`logout`。
- [x] 在 `hermes_cli/main.py` 增加顶层 `hermes team` 子命令。

## GTC-46：CLI `team_context` 注入

- [x] 在 CLI 创建 `AIAgent` 前解析当前团队上下文。
- [x] `team_cloud.enabled=false` 时不传 `team_context`。
- [x] `team_cloud.enabled=true` 且上下文完整时传入 `team_context`。
- [x] oneshot、TUI 和 background agent 同步该规则。

## GTC-47：prompt/status UX

- [x] `/team status` 显示 mode、remote、URL、org、team、project、member、role。
- [x] 团队身份显示集中在 `/team status`，避免覆盖本地 profile 语义。
- [x] `hermes team status` 提供非交互查询。

## GTC-48：Team Cloud 身份验证闭环

- [x] CLI 调 Team Cloud `/v1/auth/login` 获取 session token。
- [x] CLI `status` 调 `/v1/auth/session` introspection 验证当前 session。
- [x] 普通成员使用 `client=cli` 登录，不再设计 service token 模式。
- [x] 配置不完整或 token 缺失时 fail closed，不传入本地伪造的 `team_context`。

## GTC-49：文档和 release manual 更新

- [x] 更新 `team-cloud-ga-release-manual.md`。
- [x] 更新 `team-cloud-go-minikube-dashboard-manual.md`。
- [x] 增加 CLI 团队模式使用说明。

## GTC-50：CLI 团队模式 GA 验证

- [x] 单元测试覆盖 config、command registry、login、status、team_context 解析。
- [x] Go API 测试覆盖普通成员 CLI 登录和 session introspection。
- [x] 复跑 memory provider 初始化验证 `team_context`。

## GTC-68：Team Cloud 记忆运行时自动挂载

- [x] `team_cloud.enabled=true` 且 URL、成员 token、`team_context` 完整时，`AIAgent` 自动挂载 `TeamMemoryProvider`。
- [x] 显式“增加团队记忆”由 `team_memory_add` 写入 Team Cloud `/v1/memory`，创建 `status=active`、`scope=team_shared` 的团队记忆。
- [x] `team_memory_propose` 保留为“提交审核候选”语义，不再承担直接新增 active 团队记忆。
- [x] 复合工具集显式为 `hermes-cli` 时，只要最终工具面含本地 `memory` 工具，也会注入 Team Cloud memory provider 工具。
- [x] 文档补清自动 observation、自动抽取和 prefetch 加载边界。
