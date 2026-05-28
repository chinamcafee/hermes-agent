# Team Cloud Admin Dashboard V2 改造步骤

日期：2026-05-23

## 工作包

| ID | 工作包 | 主要产出 | 前置 | 状态 |
| --- | --- | --- | --- | --- |
| GTC-51 | Dashboard V2 职责边界冻结 | 产品设计、任务拆解、进度和日志 | GTC-50 | Done |
| GTC-52 | Bootstrap V2 后端契约 TDD | 初始化状态、单团队空间、唯一超级管理员、配置检查测试 | GTC-51 | Done |
| GTC-53 | Dashboard 登录与成员角色后端 TDD | 帐号密码登录、直接创建成员、角色限制测试 | GTC-52 | Done |
| GTC-54 | Runtime config 持久化 | PostgreSQL/MinIO runtime config API 和文档 | GTC-52 | Done |
| GTC-55 | Dashboard V2 client 契约 | 新 bootstrap、login、members API client 和测试 | GTC-53 | Done |
| GTC-56 | 独立初始化引导页 | 未初始化只展示引导，配置和超级管理员分步完成 | GTC-55 | Done |
| GTC-57 | 专业管理台页面重构 | 概览、成员、权限、记忆、备份、审计、本地连接 | GTC-56 | Done |
| GTC-58 | release manual 更新 | GA 手册和 minikube 手册切换到 Dashboard V2 | GTC-57 | Done |
| GTC-59 | Dashboard V2 GA 验证 | Go、Dashboard、build、文档一致性验证 | GTC-58 | Done |
| GTC-66 | 记忆治理 CRUD 和来源标签 | 团队记忆列表、管理员创建、编辑、停用、硬删除、来源标签 | GTC-59 | Done |
| GTC-67 | 记忆治理弹窗化操作流 | 创建、编辑、审核从 Tab 常驻表单改为弹窗流程 | GTC-66 | Done |

## 执行原则

- 允许破坏性调整未上线的 Team Cloud Go Dashboard 和 API。
- 后端测试先行；每个行为调整先补 Go 或 Vitest 失败测试。
- Dashboard 第一版只暴露一个团队的管理模型；保留 org_id 作为内部兼容字段。
- UI 不再把 JSON 输出作为主要反馈形式，JSON 只作为调试详情。

## GTC-52：Bootstrap V2 后端契约 TDD

- [x] 编写失败测试：`GET /v1/bootstrap/status` 返回 database/minio/team-space/super_admin 检查项。
- [x] 编写失败测试：`POST /v1/bootstrap/super-admin` 必须接收团队名、超级管理员密码并创建单团队空间。
- [x] 实现最少后端逻辑。
- [x] 运行 `cd team_cloud && go test ./internal/httpapi -run 'TestBootstrap' -count=1`。

## GTC-53：Dashboard 登录与成员角色后端 TDD

- [x] 编写失败测试：超级管理员可登录并获得 Dashboard session token。
- [x] 编写失败测试：超级管理员可创建管理员和用户。
- [x] 编写失败测试：管理员只能创建用户。
- [x] 实现密码 hash、session token 和角色限制。
- [x] 运行 `cd team_cloud && go test ./internal/httpapi -run 'TestDashboardAuth|TestMember' -count=1`。

## GTC-54：Runtime config 持久化（已由 GTC-60~64 退役）

- [x] 2026-05-23 曾实现 runtime config 持久化。
- [x] 2026-05-24 已按新需求移除 `/v1/bootstrap/runtime-config`、`TEAM_CLOUD_RUNTIME_CONFIG_PATH` 和 Dashboard 连接配置表单。
- [x] PostgreSQL、Redis、MinIO/S3 连接统一由 Kubernetes Secret / env 注入。

## GTC-55 到 GTC-57：Dashboard V2 前端

- [x] 先写 Vitest/Testing Library 测试覆盖未初始化 gate、登录、成员列表和页面导航。
- [x] 重构 `teamCloudClient.ts`，提供 Dashboard V2 API。
- [x] 重构 `page.tsx`，将初始化引导和管理台分层。
- [x] 重写 `globals.css`，为不同页面提供不同布局组件。
- [x] 运行 `cd team_cloud/dashboard && npm test -- --run && npm run type-check && npm run build`。

## GTC-58 到 GTC-59：文档与验证

- [x] 更新 `teamDoc/releaseManual/team-cloud-ga-release-manual.md`。
- [x] 更新 `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`。
- [x] 更新 `team_cloud/README.md`。
- [x] 运行 Go、Dashboard、Docker/YAML 和 `git diff --check` 验证。

## GTC-66：记忆治理 CRUD 和来源标签

- [x] 编写失败测试：团队记忆来源字段、编辑、停用和硬删除生命周期。
- [x] 编写失败测试：Dashboard client 记忆治理 API contract。
- [x] 编写失败测试：Dashboard 记忆治理工作台渲染。
- [x] 后端 `MemoryItem` 增加 `source_type`、`source_member_id`、`created_by_member_id`。
- [x] Dashboard 记忆治理页增加团队记忆库、管理员创建、编辑、停用和彻底删除。
- [x] 完整运行 Go、Dashboard build 和文档一致性验证。

## GTC-67：记忆治理弹窗化操作流

- [x] 编写失败测试：记忆治理 Tab 默认不展示创建、编辑、审核表单。
- [x] 编写失败测试：新建团队记忆通过“创建团队记忆”弹窗完成。
- [x] 编写失败测试：列表行“编辑”通过“编辑团队记忆”弹窗完成。
- [x] 编写失败测试：待审队列行“审核”通过“审核团队记忆”弹窗完成。
- [x] 完整运行 Dashboard 测试、类型检查、构建和文档差异验证。
