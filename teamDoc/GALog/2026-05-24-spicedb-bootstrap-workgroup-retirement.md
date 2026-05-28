# 2026-05-24 SpiceDB Bootstrap Bug 与工作组退役日志

## 问题复现

- Dashboard 填完“超级管理员信息”后点击下一步，远程 SpiceDB 返回 `authz_remote_status_400`。
- 错误指向 `updates[0].operation` 和 `subject.object.object_id`。
- 继续点击“完成初始化”返回 `already_initialized`。

## 根因

- SpiceDB HTTP API 不接受旧 payload 中的 operation 值。
- 本地成员 ID 使用 `org:user`，直接作为 SpiceDB object id 时包含非法 `:`。
- bootstrap 旧流程在远程授权前已经写入团队/成员，导致远程授权失败后状态被判定为已初始化。
- 初始化 UI 仍保留默认工作组概念，与第一版“团队 + 团队成员”二级层级冲突。

## 修改记录

- 将 SpiceDB write relationship operation 改为 `OPERATION_TOUCH`。
- 增加 SpiceDB object id sanitizer，仅影响远程 payload。
- bootstrap 改为先写 `organization#owner` relationship，再持久化团队空间和超级管理员。
- `GET /v1/bootstrap/status` 改为 `organization_count + super_admin_count` 判定初始化，不再返回 `team_count`。
- 移除 `tcg_teams` 表创建、`CreateTeam/ListTeams` contract、teams endpoint 和 Dashboard team client。
- 团队共享记忆与 runtime 权限改为检查 `organization:{org_id}`。
- Kubernetes SpiceDB schema 删除 `definition team`，organization 直接承载团队级权限；管理权限命名为 `manage`，避免和 `relation admin` 重名。
- 文档同步更新为单团队空间和三步初始化模型。

## 已运行验证

```bash
cd team_cloud
go test ./...
go vet ./...
go build ./...

cd dashboard
npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx
npm run type-check
npm run build

cd ../..
git diff --check -- team_cloud teamDoc
```

## minikube Fresh Redeploy

已完成：

- 删除并重建 `hermes-team-cloud` namespace。
- 清理 minikube hostpath PV 数据。
- 重新部署 PostgreSQL/pgvector、SpiceDB、MinIO、Redis。
- 重建并加载最新 `hermes-team-cloud-go:minikube` 镜像。
- 重新部署 Team Cloud Go 2 副本。
- 重新创建 MinIO `local/hermes-personal-backups` bucket。
- 启动本地 port-forward：`http://127.0.0.1:8780/dashboard/`。

现场验证：

```bash
kubectl get pods -n hermes-team-cloud -o wide
kubectl get configmap -n hermes-team-cloud hermes-team-cloud-go-authz-schema -o jsonpath='{.data.schema\.json}'
kubectl logs -n hermes-team-cloud deployment/spicedb --since=2m
curl -sS http://127.0.0.1:8780/healthz
curl -sS http://127.0.0.1:8780/readyz
curl -sS http://127.0.0.1:8780/v1/bootstrap/status
curl -sSI http://127.0.0.1:8780/dashboard/
```

结果：

- `hermes-team-cloud-go` 两个 Pod 均为 `1/1 Running`，PostgreSQL、SpiceDB、MinIO、Redis 均为 `Running`。
- SpiceDB schema ConfigMap 已使用 `permission manage = owner + admin`，不再使用和 `relation admin` 冲突的 permission 名。
- 最近 2 分钟 SpiceDB 日志无新增 schema write 错误。
- `/healthz` 返回 `status=ok`。
- `/readyz` 返回 `status=ready`。
- `/v1/bootstrap/status` 返回 `initialized=false`、`organization_count=0`、`owner_count=0`、`super_admin_count=0`。
- `/dashboard/` 返回 `HTTP/1.1 200 OK`。
