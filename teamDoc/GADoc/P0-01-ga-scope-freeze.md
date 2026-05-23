# P0-01 GA 范围冻结决策

日期：2026-05-22
状态：Frozen for P0 execution
适用范围：Hermes Agent 企业版团队功能、双层记忆、本地记忆定时备份、Team Cloud 控制面

## 决策

Hermes Team Agent GA 只承诺可自托管、可审计、可权限隔离、可备份恢复的企业版团队 Agent 能力。GA 范围以 `Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO + Team Cloud + Hermes runtime` 为固定架构边界，任何替代身份系统、替代授权引擎或第三方托管记忆服务只能作为后续扩展，不能替代 GA 默认路径。

## GA 必须项

| 领域 | 必须交付 |
| --- | --- |
| 身份认证 | Casdoor OIDC 登录、JWT/JWKS 校验、成员状态校验、Gateway 外部身份绑定、PAT 和 service account token |
| 资源授权 | SpiceDB schema、关系同步 outbox、所有管理 API/记忆/工具调用的 permission check、权限解释最小能力 |
| Team Cloud | Go API 服务端、worker 编排边界、配置和 secret 分层、request context、健康检查、结构化日志和基础审计 |
| 数据底座 | PostgreSQL canonical schema、pgvector embedding 检索、迁移可重复执行、审计和 outbox 基表 |
| 双层记忆 | `personal` 和 `team_shared` 两级记忆、隔离召回、团队记忆审核、observation pipeline、TeamMemoryProvider |
| 本地记忆定时备份 | 个人 backup policy、加密 JSONL/ZIP manifest、MinIO 上传、下载、preview restore、restore execute、checksum 校验 |
| Hermes runtime 集成 | `AIAgent.team_context`、TeamMemoryProvider 初始化/召回/同步、API/Gateway identity propagation、runtime event bridge |
| 工具治理 | 工具风险 taxonomy、TeamToolPolicyHook、高危工具审批、工具调用审计 |
| 管理台/API | 组织、团队、项目、成员、角色、服务账号、审计、记忆、备份、导出删除的最小可用管理能力 |
| 部署与发布 | 本地 compose、Helm 或等价部署包、备份恢复 Runbook、升级/回滚文档、SBOM 和许可证说明 |
| 验收 | 跨 org、跨 member personal memory、team_shared、backup、tool bypass 的反向测试为 0 成功 |

## Beta 可缺项

| 领域 | Beta 可裁剪内容 | GA 前补齐条件 |
| --- | --- | --- |
| 部署形态 | Offline bundle 可延后 | GA 发布前提供镜像包、校验和、安装脚本 |
| Gateway 覆盖 | Beta 只覆盖 2 个主平台 | GA 前至少完成目标客户需要的平台绑定和回归 |
| Web Console 深度 | Beta 可先覆盖管理和诊断最小页 | GA 前补齐 empty/error/permission/loading 状态和关键批量操作确认 |
| 权限解释 | Beta 可展示 decision 和基础关系路径 | GA 前补齐最近关系变更、相关审计和 deny reason |
| 性能调优 | Beta 可先建立基线 | GA 前达到 prefetch P95、SpiceDB check P95 和 backup success 目标 |
| 国际化和无障碍 | Beta 可先中英文核心文案 | GA 前完成关键管理路径键盘可用性和可读性检查 |

## 明确不做项

| 不做项 | 原因 |
| --- | --- |
| 不把本地 Dashboard token 当团队登录 | 不能满足企业身份、MFA、禁用传播和审计要求 |
| 不用数据库 ACL 或 prompt 规则替代 SpiceDB | 无法表达跨资源关系授权和权限解释 |
| 不把第三方 memory provider 当 canonical memory | 权限边界、数据治理和备份恢复不可控 |
| 不新增第一版 `project_shared` 独立记忆概念 | `team_shared + project_id` 已覆盖第一版需求 |
| 不支持管理员静默下载个人备份 | 违反个人记忆隔离和 break-glass 双人审批原则 |
| 不将 Team Cloud 逻辑硬编码进现有 memory provider | 后续 provider 和 runtime 扩展必须保持插件/接口边界 |
| 不承诺闭源 SaaS 作为核心依赖 | 违反源码可访问组件策略和私有化部署目标 |

## 裁剪规则

1. 任何裁剪不得破坏四条硬边界：Casdoor 负责身份，SpiceDB 负责授权，PostgreSQL 保存 canonical memory，MinIO 保存备份和对象。
2. 任何裁剪不得降低隔离验收：跨组织、跨成员 personal memory、跨成员 backup、工具权限绕过必须保持 0 成功。
3. Beta 可裁剪体验和部署广度，不可裁剪安全、审计、备份恢复、权限反向测试。
4. 若工作包需要改变默认技术选型，必须新增 ADR 并通过 P0 架构冻结审查。
5. 未进入 GA 范围的能力只能进入 Post-GA backlog，不能阻塞 P1-P5 主路径。

## 验收证据

- 来源规格：`teamDoc/README.md`、`teamDoc/03-target-architecture.md`、`teamDoc/04-memory-design.md`、`teamDoc/12-ga-product-requirements.md`、`teamDoc/15-minio-personal-backup.md`、`teamDoc/16-ga-test-release-checklist.md`
- 追踪项：`teamDoc/GAStep/progress-tracker.md` 中 `P0-01`
