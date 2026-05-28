# GTC-51 到 GTC-59 Team Cloud Admin Dashboard V2

日期：2026-05-23

## 新增需求摘要

Dashboard V2 将 Team Cloud Admin 从 API 调试台升级为服务端产品控制面：

- 首次初始化引导页独立于后台管理台，不再作为 Tab。
- 初始化必须覆盖 PostgreSQL、MinIO、团队和唯一超级管理员。
- 管理台第一版只暴露单团队模型，不把多组织、多租户作为显性业务层级。
- 后台帐号体系为 `super_admin`、`admin`、`user`。
- 成员支持后台直接创建，不以邀请作为唯一创建方式。
- 各功能页按业务定位重构，避免表单堆叠和 JSON 主反馈。

## 破坏性调整

- Dashboard 不再展示“组织”Tab；内部 `org_id` 仅作为后端兼容字段。
- Bootstrap API 从“创建组织 Owner”升级为“创建团队和唯一超级管理员”。
- Dashboard 管理态应优先使用帐号密码登录后的 session token，不再依赖长期输入 service token。
- 旧 invite 语义保留为 API 兼容，但不是 V2 Dashboard 主入口。

## 验收证据

GTC-59 已完成以下验证：

- `cd team_cloud && go test ./...`：通过。
- `cd team_cloud && go vet ./...`：通过。
- `cd team_cloud && go build ./cmd/team-cloud-server`：通过。
- `cd team_cloud/dashboard && npm test -- --run`：2 个 test files、7 个 tests 通过。
- `cd team_cloud/dashboard && npm run type-check`：通过。
- `cd team_cloud/dashboard && npm run build`：通过。
- `cd team_cloud/dashboard && npm audit --audit-level=moderate`：0 vulnerabilities。
- `git diff --check -- team_cloud teamDoc`：通过。
- `rg -n "初始化页|初始化 Tab|组织 Tab|组织页|创建第一个组织 Owner|组织 Owner|service token 完成首次初始化|邀请成员" teamDoc/releaseManual teamDoc/17-team-cloud-go-service-design.md team_cloud/README.md team_cloud/dashboard/src`：无匹配。

## 当前实现记录

- 后端 bootstrap V2 已支持 `organization_count`、`super_admin_count`、`postgres_configured`、`minio_configured`。
- `POST /v1/bootstrap/super-admin` 已升级为创建单团队空间和唯一 `super_admin`；默认工作组维度已在 2026-05-24 退役。
- 2026-05-24 更新：`PUT /v1/bootstrap/runtime-config` 已退役，PostgreSQL/Redis/MinIO 配置改由 Secret/env 注入。
- 如果 runtime config 写入 PostgreSQL DSN 但服务尚未重启为 PostgreSQL 后端，`POST /v1/bootstrap/super-admin` 返回 `postgres_restart_required`，避免把首次初始化写入内存后端。
- `POST /v1/auth/login` 已支持 Dashboard 帐号密码登录并签发 `hcs_...` Redis session token。
- `POST /api/organizations/{org_id}/members` 已支持直接创建管理员和用户，并强制管理员只能创建用户。
- `PATCH /api/organizations/{org_id}/members/{member_id}` 已支持编辑成员邮箱和显示名。
- 成员页已补齐查询、角色筛选、编辑和停用动作；唯一超级管理员不可停用。
- Dashboard 前端已重构为独立初始化引导、登录页和已登录管理台三层。
