# Team Cloud Admin Dashboard V2 改造日志

日期：2026-05-23

> 2026-05-24 更新：本日志中的 `hermes-dashboard-v1.*`、runtime config 和 service token bootstrap 记录已被 GTC-60~64 取代；默认工作组、`team_count` 和 team owner 关系已被 GTC-65 取代。当前 GA 口径为无 service token 初始化、Secret/env 注入连接配置、Redis 保存 `hcs_...` Dashboard session token，以及单团队空间模型。

## GTC-51

- 新增 `teamDoc/19-team-cloud-dashboard-v2-product-design.md`。
- 新增 `teamDoc/GAStep/10-team-cloud-dashboard-v2-steps.md`。
- 新增 `teamDoc/GADoc/GTC-51-59-team-cloud-dashboard-v2.md`。
- 明确 Dashboard V2 的独立初始化引导、单团队管理、三级角色和专业化页面职责。

## 后续记录

编码和验证推进过程中持续追加。

## GTC-52

- 扩展 `GET /v1/bootstrap/status`：新增 `super_admin_count`、`postgres_configured`、`minio_configured`；2026-05-24 起 `team_count` 已退役。
- 扩展 `POST /v1/bootstrap/super-admin`：创建单团队空间、唯一 `super_admin`，并写入 organization owner 关系。
- 超级管理员密码使用 bcrypt hash 保存，API 响应不返回 hash。
- 验证：`go test ./internal/httpapi -run 'TestBootstrapStatusReportsDashboardV2RequiredConfiguration|TestBootstrapSuperAdminCreatesOwnerAndRejectsRepeatedInitialization' -count=1`。

## GTC-53

- 新增 Dashboard session token：`POST /v1/auth/login` 使用帐号密码登录，返回 `hermes-dashboard-v1.*` token。
- 新增 `POST /api/organizations/{org_id}/members` 直接创建后台成员帐号。
- 超级管理员可创建管理员和用户；管理员只能创建用户。
- 验证：`go test ./internal/httpapi -run 'TestDashboardLoginAndDirectMemberCreationRoleLimits' -count=1`。

## GTC-54

- 新增 `TEAM_CLOUD_RUNTIME_CONFIG_PATH` 和 runtime config JSON overlay。
- 新增 `PUT /v1/bootstrap/runtime-config`，由 service token 保存 PostgreSQL 和 MinIO/S3 必填配置。
- 保存 runtime config 后返回 `restart_required`，用于提示 PostgreSQL 后端切换需要重启服务。
- 验证：`go test ./internal/config ./internal/httpapi -run 'TestFromEnvOverlaysRuntimeConfigFile|TestBootstrapRuntimeConfig' -count=1`。
- 补充验证：`go test ./internal/httpapi -count=1`。

## GTC-55

- 重写 `team_cloud/dashboard/src/lib/teamCloudClient.ts`，新增 Dashboard V2 bootstrap、runtime config、login 和 direct member API。
- 更新 client 测试，覆盖 service token bootstrap、Dashboard session token 管理 API 和新 bootstrap payload。
- 验证：`cd team_cloud/dashboard && npm test -- --run`。

## GTC-56

- 重写 `team_cloud/dashboard/src/app/page.tsx`，未初始化时只展示独立初始化引导页。
- 初始化引导页分为 PostgreSQL、MinIO、团队、超级管理员四类状态和两组主要操作。
- 移除“初始化 Tab”和“组织 Tab”作为一级管理导航。

## GTC-57

- 管理台改为登录后进入，使用 `hermes-dashboard-v1.*` session token。
- 管理页重构为概览、团队成员、权限中心、记忆治理、备份策略、审计时间线、本地连接。
- 团队成员页以列表和抽屉表单为主，权限/记忆/备份/审计页面采用不同信息架构。
- 验证：`npm test -- --run`、`npm run type-check`、`npm run build`。

## GTC-58

- 更新 `team_cloud/README.md`，补充 Dashboard V2、runtime config、登录 session 和直接创建成员 API。
- 更新 `teamDoc/17-team-cloud-go-service-design.md`，同步 bootstrap V2、runtime config 和 Dashboard session 边界。
- 更新 `teamDoc/releaseManual/team-cloud-ga-release-manual.md` 和 `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`，改为独立初始化引导和登录式管理台流程。

## GTC-59

- `cd team_cloud && go test ./...`：通过。
- `cd team_cloud && go vet ./...`：通过。
- `cd team_cloud && go build ./cmd/team-cloud-server`：通过。
- `cd team_cloud/dashboard && npm test -- --run`：2 个 test files、7 个 tests 通过。
- `cd team_cloud/dashboard && npm run type-check`：通过。
- `cd team_cloud/dashboard && npm run build`：通过。
- `cd team_cloud/dashboard && npm audit --audit-level=moderate`：0 vulnerabilities。
- `git diff --check -- team_cloud teamDoc`：通过。

## 复查补齐

- 成员管理页补齐查询、角色筛选、编辑基础资料和停用动作。
- 后端补齐 `PATCH /api/organizations/{org_id}/members/{member_id}`，用于编辑成员邮箱和显示名。
- 本地连接页复制按钮改为调用 Clipboard API。
- 同步修正 `teamDoc/GAStep/10-team-cloud-dashboard-v2-steps.md` 中已完成工作包和清单状态。
- 补充验证要求：超级管理员不可被停用，避免唯一最高权限帐号被管理台误操作删除。
