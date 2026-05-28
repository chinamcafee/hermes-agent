# Hermes Team Agent GA 产品化方案

调研日期：2026-05-22

本文档集以 GA 产品形态为目标，说明如何基于当前 `hermes-agent` 建设开箱即用的团队版 Agent。目标不是做一个演示版插件，而是交付可私有化部署、可审计、可运营、可长期维护的团队 Agent 产品。

## 目标能力

- 团队成员共同使用，支持 Web/API/Gateway 多入口和跨平台身份绑定。
- 长期团队记忆云同步；个人记忆和本地人格保留在本地 Hermes profile，并通过 CLI 自助备份。
- 团队帐号、组织、成员、角色、服务账号、API token 和细粒度权限管理。
- 云端数据管理，覆盖会话、消息、工具调用、记忆、文档、审计、导出、删除和备份恢复。
- 所有新引入组件源码可访问，不使用仅闭源商业服务作为核心依赖。

## 指定 GA 技术框架

本轮方案限定在以下技术框架内：

| 层级 | 选型 | 职责 |
| --- | --- | --- |
| 身份认证 | Casdoor | OIDC/OAuth/SAML/LDAP/SCIM、用户登录、MFA、组织和应用管理 |
| 资源授权 | SpiceDB | Google Zanzibar 风格 ReBAC，承载团队、项目、记忆、文档、工具等资源级权限 |
| 结构化与向量存储 | PostgreSQL + pgvector | canonical data、会话、记忆、embedding、审计、数据治理 |
| 本地备份与对象存储 | MinIO/S3-compatible（可选） | CLI `/cloud-backup` 的个人记忆和本地人格备份目标、Team Cloud 团队记忆和团队父人格备份对象存储；不是服务端初始化必备组件 |
| Hermes runtime | hermes-agent | Agent loop、Gateway、API Server、工具、skills、MemoryProvider |
| Team Cloud | 自研 Go 服务 + Next.js 静态 Dashboard | 产品控制面、Memory API、权限网关、首次初始化、团队管理台、worker 编排和 Kubernetes 部署入口 |

## 核心结论

Hermes 已经具备团队版 runtime 基础，但 GA 产品需要新增 Team Cloud 控制面：

- `hermes-agent` 保持 Agent runtime，不承载团队 SaaS 的最终身份和权限边界。
- Team Cloud 首次上线部署目标为 `team_cloud/` Go 服务；旧 Python 服务端已经删除，后续源码、脚本和文档均以该 Go 目录为准。
- Casdoor 作为唯一默认身份系统，Team Cloud 只信任 Casdoor 签发的 OIDC/JWT 和同步事件。
- SpiceDB 作为唯一默认资源授权系统，所有跨成员、跨团队、跨项目、跨记忆读取必须走 `CheckPermission`。
- PostgreSQL + pgvector 保存 Team Cloud canonical team memory，不把任何第三方 memory provider 当作权限边界。
- Team Cloud Go 管理团队父人格；Hermes Agent 在 team mode 本地人格保存后调用当前模型供应商生成 effective soul，失败时优雅提示并使用安全降级组合。
- MinIO/S3-compatible 对象存储改为可选：CLI `/cloud-backup memory|soul` 管理个人记忆和本地人格备份；Team Cloud 仅在启用团队记忆或团队父人格备份对象存储时使用它。

## GA 工作量判断

| 阶段 | 目标 | 推荐团队 | 日历时间 | 工作量 |
| --- | --- | ---: | ---: | ---: |
| GA Foundation | Casdoor、SpiceDB、PostgreSQL/pgvector、MinIO、Team API、基础 Web 管理台、Hermes identity propagation | 4-5 人 | 10-14 周 | 50-75 人周 |
| GA Beta | 本地个人记忆 + 云端团队记忆边界、工具权限、审计、CLI 个人备份、Gateway 绑定、导入导出、压测和安全测试 | 5-6 人 | 10-12 周 | 60-85 人周 |
| GA Release | 企业部署、SSO/SCIM 流程、备份恢复演练、权限解释、升级迁移、SLO/Runbook、合规验收 | 6-8 人 | 8-12 周 | 55-80 人周 |

总量约 `165-240 人周`，日历时间约 `7-9 个月`。如果只做内部 Beta 可以裁剪到 4-5 个月，但不应标记为 GA。

## 文档索引

- [00-current-hermes-capabilities.md](00-current-hermes-capabilities.md) - Hermes 现有能力盘点。
- [01-gap-analysis.md](01-gap-analysis.md) - GA 需求拆解和缺口矩阵。
- [02-technical-selection.md](02-technical-selection.md) - 指定技术选型和边界。
- [03-target-architecture.md](03-target-architecture.md) - GA 目标架构。
- [04-memory-design.md](04-memory-design.md) - PostgreSQL/pgvector 双层长期记忆设计。
- [05-auth-permission-design.md](05-auth-permission-design.md) - Casdoor + SpiceDB 身份权限方案。
- [06-cloud-data-management.md](06-cloud-data-management.md) - 云端数据管理和 MinIO 备份方案。
- [07-roadmap-and-estimate.md](07-roadmap-and-estimate.md) - GA 路线图、工作量和团队配置。
- [08-risks-and-validation.md](08-risks-and-validation.md) - 风险、测试和验收标准。
- [09-references.md](09-references.md) - 本次调研引用的本地代码与外部资料。
- [10-implementation-backlog.md](10-implementation-backlog.md) - 可直接拆任务的 GA Backlog。
- [11-source-accessible-component-policy.md](11-source-accessible-component-policy.md) - 源码可访问组件准入策略。
- [12-ga-product-requirements.md](12-ga-product-requirements.md) - GA 产品需求与验收口径。
- [13-casdoor-spicedb-integration.md](13-casdoor-spicedb-integration.md) - Casdoor 与 SpiceDB 集成细节。
- [14-postgres-pgvector-memory-schema.md](14-postgres-pgvector-memory-schema.md) - PostgreSQL/pgvector 记忆库详细 schema。
- [15-minio-personal-backup.md](15-minio-personal-backup.md) - MinIO 本地 memory/soul 云备份与恢复设计。
- [16-ga-test-release-checklist.md](16-ga-test-release-checklist.md) - GA 测试、发布和运维检查清单。
- [17-team-cloud-go-service-design.md](17-team-cloud-go-service-design.md) - Team Cloud 服务端设计与部署边界。
- [18-hermes-cli-team-context-boundary.md](18-hermes-cli-team-context-boundary.md) - Hermes CLI 本地个人模式和 Team Cloud 团队上下文边界、一等命令与使用规则。
- [19-team-cloud-dashboard-v2-product-design.md](19-team-cloud-dashboard-v2-product-design.md) - Team Cloud Admin Dashboard V2 初始化引导、单团队管理和角色体系设计。
- [20-desktop-team-bridge-boundary.md](20-desktop-team-bridge-boundary.md) - Hermes Desktop 通过 Hermes Agent CLI/API Bridge 接入 Team Cloud 的职责边界。
- [ThreePartyUnionDevDoc/README.md](ThreePartyUnionDevDoc/README.md) - Hermes Agent、Team Cloud、Hermes Desktop 围绕团队父人格、effective soul 和 `/cloud-backup` 的三方联动方案。
- [GAStep/README.md](GAStep/README.md) - 从 0 改造到 GA 的细粒度编码步骤和进度追踪入口。
- [releaseManual/team-cloud-go-minikube-dashboard-manual.md](releaseManual/team-cloud-go-minikube-dashboard-manual.md) - minikube 本地 Kubernetes 部署 Team Cloud + Dashboard + 中间件并连接本地 Hermes 的手册。
