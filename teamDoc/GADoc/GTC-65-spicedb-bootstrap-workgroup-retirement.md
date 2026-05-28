# GTC-65 SpiceDB Bootstrap Bug 修复与工作组维度退役

日期：2026-05-24

## 背景

Dashboard 初始化在“超级管理员信息”后写远程 SpiceDB relationship 时出现 `authz_remote_status_400`。错误包含两个根因：

- HTTP payload 使用了 SpiceDB 不接受的 relationship update operation 值。
- 本地成员 ID 使用 `org:user` 形式，直接写入 SpiceDB `object_id` 时不符合 SpiceDB object id 正则。

随后点击“完成初始化”返回 `already_initialized`，是因为旧流程先落库团队/成员，再写远程授权；远程授权失败后已经留下部分初始化数据。

## 设计决策

- SpiceDB HTTP 写关系统一使用 `OPERATION_TOUCH`。
- 仅在远程 SpiceDB payload 中转换 object id：`:` 转为 `|`，其他非法字符转为 `_`；本地 PostgreSQL/API ID 保持不变。
- 初始化先写远程 `organization#owner` relationship，再创建团队空间和超级管理员成员，避免授权失败后留下半初始化数据。
- 第一版退役“默认工作组/子团队”维度：初始化只需要团队名称和超级管理员信息。
- `tcg_teams` 表、`CreateTeam/ListTeams` store contract、`/api/organizations/{org_id}/teams` API 和 Dashboard team client 全部退役。
- 团队共享记忆、运行时和权限检查统一以 `organization:{org_id}` 作为团队级资源；`team_id` 字段仅作为历史兼容输入，不代表可管理工作组实体。
- Kubernetes SpiceDB schema 删除 `definition team`，在 `definition organization` 上声明 `read_team`、`write_team`、`review`、`run_agent` 和 `use` 权限。
- SpiceDB schema 中保留 `relation admin`，管理权限命名为 `permission manage`，避免 relation/permission 同名导致 schema write 失败。

## 代码产出

- `team_cloud/internal/authz/authz.go`：修复 SpiceDB HTTP operation 和 object id sanitizer。
- `team_cloud/internal/httpapi/bootstrap.go`：初始化顺序改为授权先行，状态不再返回 `team_count`。
- `team_cloud/internal/store/store.go`：移除 `Team` 和 `CreateTeam/ListTeams` contract。
- `team_cloud/internal/store/postgres/schema.go`：停止创建 `tcg_teams`，迁移时 destructive drop 旧表。
- `team_cloud/internal/store/postgres/store.go`、`internal/store/memory/store.go`：团队共享记忆不再要求 `team_id`。
- `team_cloud/internal/httpapi/server.go`：移除 teams endpoint，团队级鉴权改为 organization 资源。
- `team_cloud/dashboard/src/app/page.tsx`、`teamCloudClient.ts`：初始化三步化，权限检查默认使用 organization 资源。
- `team_cloud/deploy/kubernetes/team-cloud-go.yaml`：SpiceDB schema 改为单团队空间模型。

## 验证

已覆盖：

- SpiceDB HTTP payload operation 和 object id sanitizer 单测。
- bootstrap 远程授权失败不落库、不会触发后续 `already_initialized` 的回归测试。
- bootstrap status 不再暴露 `team_count`。
- teams endpoint 退役测试。
- PostgreSQL schema 不再创建 `tcg_teams`，且会删除旧表。
- Dashboard 初始化页不再出现默认工作组字段。

命令：

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

## minikube Fresh Smoke

2026-05-24 已清理并重建 `hermes-team-cloud` namespace、PostgreSQL/pgvector、SpiceDB、MinIO、Redis 和 `hermes-team-cloud-go:minikube` 镜像。

当前验收入口：

```text
http://127.0.0.1:8780/dashboard/
```

运行状态：

- Team Cloud Go 副本数：2/2 Running。
- PostgreSQL、SpiceDB、MinIO、Redis：全部 Running。
- SpiceDB schema init container：Completed，exit code 0。
- `kubectl logs deployment/spicedb --since=2m`：无新增 schema write 错误。
- `/healthz`：`status=ok`。
- `/readyz`：`status=ready`，authz、backend、backup object store、config、session store 均为 true。
- `/v1/bootstrap/status`：`initialized=false`、`organization_count=0`、`owner_count=0`、`super_admin_count=0`，可用于全新初始化验收。
