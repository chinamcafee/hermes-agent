# Team Cloud Admin Dashboard V2 产品与技术设计

日期：2026-05-23

## 背景

当前 `team_cloud/dashboard` 已经随 Go 服务部署，但交互仍偏向 API 调试台：初始化、组织、权限、记忆、备份等页面都以表单和 JSON 输出为主，业务层级不清晰，也没有区分“首次初始化引导”和“后台管理工作台”。

V2 改造的目标是把 Dashboard 定义为 Team Cloud 服务端自己的产品控制面。本地 Hermes dashboard/CLI 只负责个人本地事务和 Team Cloud 连接配置，不承载云端团队管理。

## 产品边界

- 未完成初始化时，浏览器只展示独立初始化引导页，不展示管理台导航。
- 初始化引导页只负责团队和超级管理员创建；PostgreSQL、Redis 等连接由 Kubernetes Secret / env 在服务端启动前注入，引导页只展示健康状态。MinIO/S3 是团队记忆和团队父人格备份的可选对象存储，不是初始化必填项。
- 初始化完成后进入后台管理台，通过超级管理员或管理员帐号密码登录。
- 第一版只管理一个团队，不引入组织、多团队、多租户的一级概念。
- 后端仍可保留组织字段作为兼容和未来扩展点，但 Dashboard 不把“组织”作为用户可见主导航。

## 初始化模型

初始化必填项：

- PostgreSQL 连接信息：生产环境必须由环境变量或 Kubernetes Secret 提供。
- Redis 连接信息：用于保存 Dashboard 登录后的用户级 opaque session token。
- 团队名称。服务端从团队名称派生内部 `org_id`，作为第一版单团队空间标识和后续多租户扩展点。
- 唯一超级管理员帐号、邮箱、显示名和密码。

初始化状态必须同时满足：

- PostgreSQL 配置存在。
- Redis session store ready。
- Team Cloud 后端、授权层和 Dashboard 静态资源 ready。
- 已创建一个团队空间。
- 已创建且仅有一个 `super_admin`。

任一条件缺失，Dashboard 继续展示初始化引导页。

## 成员与角色

第一版角色为三级：

| 角色 | 数量 | 能力 |
| --- | ---: | --- |
| 超级管理员 `super_admin` | 1 | 只能在初始化引导页创建；可创建管理员和用户；可管理全部功能。 |
| 管理员 `admin` | 不限 | 可创建用户、管理记忆治理、备份、审计和本地连接配置。 |
| 用户 `user` | 不限 | 作为团队成员使用 Hermes，不进入后台创建管理员。 |

成员创建方式：

- Dashboard 支持直接创建帐号，不把“邀请”作为唯一入口。
- 超级管理员可创建 `admin` 和 `user`。
- 管理员只能创建 `user`。
- 旧的 invite API 可保留为兼容入口，但 Dashboard V2 不作为主路径展示。

## 管理台导航

初始化完成并登录后展示管理台：

- 概览：团队状态、服务健康、成员数、待审记忆、团队备份摘要。
- 团队成员：成员列表、搜索、角色筛选、创建成员、停用成员。
- 权限中心：只读角色能力说明和服务端固定权限矩阵，不提供后台可编辑权限关系。
- 记忆治理：团队记忆库列表、来源标签、管理员创建、编辑、停用、硬删除、待审队列和批准/拒绝操作；创建、编辑、审核均使用弹窗流程承载。
- 备份管理：团队记忆与团队父人格两类备份的策略设置、备份历史、立即备份和按历史备份恢复。
- 审计：事件时间线、动作筛选、Actor/资源检索。
- 本地连接：Hermes CLI/dashboard 连接 Team Cloud 的 URL、token 和配置片段。

页面不在一级区域直接堆表单。每个页面都应先给列表、状态、摘要或动作区，再用抽屉或对话框承载新增、编辑和审核；“记忆治理”页不允许在 Tab 首屏常驻创建、编辑、审核表单。

## 后端契约

新增或调整 API：

- `GET /v1/bootstrap/status`：返回初始化状态、必填配置检查、团队空间数量、超级管理员数量，不再返回已退役的工作组 `team_count`。
- `POST /v1/bootstrap/super-admin`：首次初始化开放调用，创建单团队空间、唯一超级管理员、帐号密码 hash 和 `organization#owner` 关系；完成后不再允许重复初始化。
- `POST /v1/auth/login`：后台帐号密码登录，返回 Redis 支撑的 `hcs_...` opaque session token。
- `POST /api/organizations/{org_id}/members`：直接创建成员帐号。
- `GET /api/organizations/{org_id}/members`：返回成员列表，隐藏密码 hash。
- `PATCH /api/organizations/{org_id}/members/{member_id}`：编辑成员邮箱和显示名。
- `GET /v1/memory?org_id=<org_id>&scope=team_shared`：返回团队记忆库列表，包含 `source_type`、`source_member_id`、`created_by_member_id`。
- `POST /v1/memory`：管理员创建团队记忆时写入 `source_type=admin_created` 和 `status=active`。
- `PATCH /v1/memory/{id}`：编辑团队记忆内容、类型和敏感度。
- `POST /v1/memory/{id}/disable`：停用团队记忆，落库为 `status=archived`。
- `DELETE /v1/memory/{id}`：彻底删除团队记忆。
- `GET /v1/team-soul?org_id=<org_id>`：读取 active 团队父人格。
- `PUT /v1/team-soul`：超级管理员或管理员更新团队父人格，并写入版本和审计。
- `GET /v1/team-soul/history?org_id=<org_id>`：读取团队父人格版本历史。
- `POST /v1/team-soul/restore-version`：从历史版本恢复团队父人格。
- `GET /v1/team-memory-backup-policy?org_id=<org_id>`：读取团队记忆备份策略。
- `PUT /v1/team-memory-backup-policy`：保存团队记忆备份策略。
- `GET /v1/team-soul-backup-policy?org_id=<org_id>`：读取团队父人格备份策略。
- `PUT /v1/team-soul-backup-policy`：保存团队父人格备份策略。
- `GET /v1/backups/team?org_id=<org_id>`：读取团队记忆备份历史。
- `POST /v1/backups/team/run`：立即执行团队记忆备份。
- `POST /v1/backups/team/{id}/restore-preview`：恢复前预览团队记忆备份。
- `POST /v1/backups/team/{id}/restore-execute`：按 memory id upsert 恢复团队记忆，重复恢复不产生重复记录。
- `GET /v1/backups/team-soul?org_id=<org_id>`：读取团队父人格备份历史。
- `POST /v1/backups/team-soul/run`：立即执行团队父人格备份。
- `POST /v1/backups/team-soul/{id}/restore-preview`：恢复前预览团队父人格备份。
- `POST /v1/backups/team-soul/{id}/restore-execute`：按 org/team active soul upsert 恢复团队父人格，重复恢复不产生多条 active soul。

## 安全要求

- 彻底移除 Dashboard bootstrap service token；首次初始化只允许在系统未初始化状态调用。
- Dashboard session token 由服务端签发，并将 token 摘要和 principal 存储在 Redis 中；后续 API 只接受 Bearer session token 或 Casdoor/JWKS JWT。
- 密码只存储强 hash，不在 API 响应中返回。
- 超级管理员唯一性由后端强制。
- 管理员创建角色必须由后端校验，不能只依赖前端禁用按钮。

## 验收标准

- 未初始化时无法看到后台 Tab，只能看到初始化引导页。
- 初始化页使用 Step-by-Step pager 体验，每一步只处理一个主题。
- 初始化页不展示 PostgreSQL DSN、MinIO access key 或 Service token 输入框。
- 初始化页能展示 PostgreSQL、Redis、可选对象存储、团队、超级管理员状态。
- 初始化成功后可以用超级管理员帐号密码登录。
- 团队成员页以列表为主，并支持直接创建管理员和用户。
- 管理员帐号登录后不能创建管理员，只能创建用户。
- 记忆治理页必须展示自动抽取和管理员创建两类来源标签，并支持团队记忆创建、编辑、停用和彻底删除；创建、编辑、审核只能在弹窗/抽屉级操作面完成。
- 备份管理页必须同时展示团队记忆备份和团队父人格备份，两类恢复都必须先调用 preview 再 execute。
- 记忆治理、备份管理、审计、本地连接页面具有各自不同的信息架构和 UI 组织方式。
- release manual 和 minikube 手册更新为 Dashboard V2 流程。
