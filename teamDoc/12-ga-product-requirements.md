# 12. GA 产品需求与验收口径

## 1. GA 定义

GA 版本必须满足：

- 新客户可通过文档完成自托管部署。
- 管理员可通过 Web Console 完成团队成员、只读权限说明、团队记忆、团队父人格和团队级备份管理。
- 普通成员可跨 Web/API/Gateway 使用同一个团队 Agent。
- 团队共同记忆、团队父人格、文档、会话和备份均可审计、导出、删除；个人记忆和本地人格由本地 Hermes profile 和 CLI `/cloud-backup memory|soul` 管理。
- Casdoor、SpiceDB、PostgreSQL/pgvector 均有备份恢复和升级 Runbook；MinIO/S3-compatible 作为可选对象存储记录配置和恢复流程。

## 2. Persona

| Persona | 目标 |
| --- | --- |
| Org Owner | 安装、配置组织、邀请管理员、查看审计、处理删除和导出 |
| Admin | 管理成员、团队、项目、connector、服务账号 |
| Security Admin | 管理工具权限、查看权限解释、审批 break-glass |
| Memory Curator | 审核团队共享记忆、处理冲突和过期 |
| Member | 使用 Agent、管理个人记忆和本地人格、配置本地 memory/soul 备份 |
| Developer | 在项目授权范围内使用开发工具 |
| Guest | 限定访问项目或频道 |
| Service Account | 自动化调用 Agent/API |

## 3. 核心用户旅程

### 组织初始化

```text
部署 Team Cloud
  -> 部署 team_cloud Go 服务端
  -> 打开 /dashboard/ 初始化服务
  -> 配置 Casdoor OIDC app
  -> 初始化 SpiceDB schema
  -> 初始化 PostgreSQL migrations
  -> 可选配置 Team Cloud 团队记忆和团队父人格备份对象存储
  -> 在 Dashboard 初始化向导创建唯一超级管理员
  -> 创建组织/team/project
  -> 邀请成员
```

验收：

- 30 分钟内完成单机开发环境部署。
- 1 小时内完成基础私有化环境部署。
- 安装失败有明确日志和健康检查定位。

### 成员使用 Agent

```text
成员登录
  -> 进入项目
  -> 发起对话
  -> TeamMemoryProvider 召回 team_shared
  -> 本地 Hermes 记忆系统召回个人记忆
  -> 工具调用被 TeamToolPolicyHook 检查
  -> 对话写入 observations
  -> worker 抽取候选记忆
```

验收：

- personal memory 只保存在当前成员本地 Hermes profile，不由 Team Cloud 查询或管理。
- team_shared memory 只影响授权团队/项目。
- 高危工具默认不静默执行。

### 本地 memory/soul 备份

```text
成员打开 Hermes CLI
  -> /cloud-backup config 配置 MinIO/S3-compatible 地址
  -> /cloud-backup memory schedule 设置个人记忆备份周期
  -> /cloud-backup soul schedule 设置本地人格备份周期
  -> /cloud-backup memory backup 生成本地 profile 个人记忆备份 JSON
  -> /cloud-backup soul backup 生成本地 profile SOUL.md 备份 JSON
  -> 上传用户指定对象存储
  -> 成员下载或恢复
```

验收：

- 成员可在 CLI 自助配置、备份、列出历史和恢复 memory/soul 两类本地资源。
- Team Cloud 管理员不管理成员个人记忆备份和本地人格备份。
- 恢复覆盖当前本地 profile 的 `memories/` 文件，用户应在恢复前确认目标 profile。
- soul 恢复覆盖当前本地 profile 的 `SOUL.md`，必须拒绝 memory/soul resource type 不匹配的恢复请求。

## 4. 功能验收

| 领域 | GA 验收 |
| --- | --- |
| AuthN | Casdoor OIDC 登录、MFA、禁用、SCIM/外部 IdP 流程可用 |
| AuthZ | SpiceDB 权限矩阵完整，所有管理 API 和工具调用受控 |
| Memory | 本地 personal 与云端 team_shared 边界清晰；团队记忆审核、召回、备份、恢复完整 |
| Soul | Team Cloud 管理团队父人格；Hermes Agent team mode 合成 effective soul；本地人格备份走 `/cloud-backup soul` |
| Gateway | 至少 2 个平台完成身份绑定和团队会话 |
| API | OpenAI-compatible 入口支持团队上下文和 token scope |
| Admin | 成员、权限说明、团队记忆、团队父人格、审计、备份和导出可视化 |
| Audit | 高危和敏感操作 100% 留痕 |
| Deployment | Kubernetes manifest、minikube runbook 和 offline bundle 覆盖部署、验收与离线交付 |

Go 服务端追加验收：

- `team_cloud/` 能独立构建 `team-cloud-server`，并且该目录就是当前唯一 Team Cloud 服务端源码。
- `team_cloud/dashboard/` 能静态构建并随 Go 服务在 `/dashboard/` 提供首次初始化和团队管理台。
- `/v1/bootstrap/status` 可无 token 检查初始化状态；`/v1/bootstrap/super-admin` 仅在未初始化时开放调用且重复初始化返回冲突。
- `TEAM_CLOUD_DATABASE_URL` 设置后使用 PostgreSQL 后端。
- Kubernetes manifest 包含 readiness/liveness probe、非 root 运行、只读根文件系统和 Secret 注入。
- 旧 Team Cloud 服务端已经删除，当前部署、测试和手册只引用 `team_cloud/` Go 服务端路径。

## 5. 非功能验收

| 指标 | GA 目标 |
| --- | ---: |
| Team API availability | >= 99.5% |
| memory prefetch P95 | <= 500ms |
| SpiceDB check P95 | <= 30ms |
| backup success rate | >= 99% |
| PostgreSQL RPO | <= 15 分钟 |
| Optional object-store RPO | <= 1 小时 |
| restore drill | 每个发布候选版本必须通过 |
| cross-tenant leakage | 0 |
| personal memory leakage | 0 |

## 6. 不接受的 GA 缺口

- 仍用临时数据库 ACL 替代 SpiceDB。
- 仍把团队云端管理功能放在本地 Hermes dashboard/CLI 中。
- 仍使用部署级 bootstrap token 作为普通成员或 Dashboard 长期登录凭据。
- CLI 个人记忆和本地人格没有自助备份和恢复。
- 团队共享记忆没有审核或来源追踪。
- 工具权限只靠 prompt 或 slash command。
- 备份恢复没有演练。
- 没有权限解释和审计导出。
- 生产环境只使用内存后端运行 Team Cloud。
