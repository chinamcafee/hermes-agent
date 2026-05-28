# GTC-60~64 Dashboard Token Redesign GA 记录

日期：2026-05-24

## 范围

本轮改造移除 Team Cloud Admin Dashboard 中的 service token bootstrap 设计，改为：

- 首次初始化不需要预置 token，只在未初始化状态允许创建单团队空间和唯一超级管理员。
- PostgreSQL、Redis、MinIO/S3 等连接信息全部通过 Kubernetes Secret / env 注入，不再由初始化页保存 runtime config。
- `POST /v1/auth/login` 使用管理页帐号密码登录，签发 `hcs_...` opaque session token。
- session token 的摘要与 principal 存储在 Redis 中；未配置 Redis 时仅开发/测试使用内存 session store。
- Dashboard 初始化页改为 Step-by-Step pager 体验，并采用 Vega Dark 风格重做视觉层级。

## 后端结果

- 移除 `TEAM_CLOUD_SERVICE_TOKEN` 配置和 service token 鉴权路径。
- 移除 `/v1/bootstrap/runtime-config` 路由。
- 新增 `TEAM_CLOUD_REDIS_ADDR`、`TEAM_CLOUD_REDIS_PASSWORD`、`TEAM_CLOUD_REDIS_DB`、`TEAM_CLOUD_SESSION_TTL_SECONDS`。
- 新增 `internal/authn/session_store.go`，实现 Redis session store 和测试用 memory session store。
- `GET /readyz` 和 `GET /v1/bootstrap/status` 增加 session store 检查。

## Dashboard 结果

- 初始化页只保留 API 地址、团队、超级管理员和确认三步。
- 第一版已退役“默认工作组”维度；团队级权限和团队共享记忆统一挂在 `organization:{org_id}`。
- 不再展示 Service token、PostgreSQL DSN、MinIO key 等输入框。
- 管理台仍保留成员、权限、记忆治理、备份、审计和本地连接功能页。
- 全局样式切换到 dark color-scheme，使用 shadcn/Vega 风格的深色 surface、stepper、状态卡、表格和按钮。

## 部署结果

- Kubernetes manifest 删除 `TEAM_CLOUD_SERVICE_TOKEN`。
- 新增 Redis Service/StatefulSet。
- Team Cloud Go Deployment 增加 Redis env。
- Redis StatefulSet 显式覆盖 entrypoint 为 `redis-server`，避免官方镜像默认 entrypoint 在 minikube PVC 上执行 `chown .` 时因卷权限限制进入 CrashLoopBackOff。

## 验证

```bash
cd team_cloud
go test ./...
go vet ./...
go build ./...

cd dashboard
npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx
npm run type-check
npm run build

kubectl get pods -n hermes-team-cloud
curl -sS http://127.0.0.1:8780/readyz
curl -sS http://127.0.0.1:8780/v1/bootstrap/status
curl -sSI http://127.0.0.1:8780/dashboard/
```
