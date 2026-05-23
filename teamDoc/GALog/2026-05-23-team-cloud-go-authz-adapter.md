# 2026-05-23 Team Cloud Go 远程授权适配日志

## 背景

当前 `team_cloud_go/` 已提供本地 relationship/check API，但 GA 手册和设计文档仍要求云端团队协作具备可部署的授权服务侧能力。为避免把远程 SpiceDB/Authzed 接入留作上线后的非阻塞项，本轮新增 GTC-18/GTC-19。

## 执行计划

1. 先补充 GTC 任务拆解和进度追踪。
2. 用失败测试定义 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 下的 relationship write、permission check 和 remote fail-closed 行为。
3. 实现 Go 1.24 兼容的标准库 HTTP adapter，不引入会升级 toolchain 的 SDK 依赖。
4. 更新 Kubernetes manifest、README、设计文档和 release manual。
5. 运行 `go test ./...`、`go vet ./...`、`go build ./cmd/team-cloud-server`、Kubernetes YAML 解析和 `git diff --check`。

## 实时记录

- 15:04 CST：新增 GTC-18/GTC-19，远程授权适配升级为 GA 阻塞收口项。
- 15:12 CST：补充远程 Authzed/SpiceDB HTTP adapter 红灯测试，确认缺少 adapter、配置字段和 readiness authz 检查。
- 15:18 CST：实现标准库 HTTP adapter、本地/远程 mirrored authorizer、`/readyz` authz fail-closed、relationship write 和 permission check 集成；局部测试通过。
- 15:31 CST：补充 JWT 业务授权红灯测试，确认 payload spoofing 和无授权成员管理会被旧实现放行。
- 15:43 CST：接入 org/member scope 守卫、高风险业务入口授权和 team_shared prefetch 授权过滤；局部测试通过。
- 15:58 CST：新增 AES-GCM JSONL exporter、S3/MinIO path-style object store、backup manifest 回写和 restore preview 持久守卫；局部测试通过。
- 16:18 CST：新增 enabled backup policy 调度 runner，服务端启动时按配置周期扫描并执行 scheduled personal backup。
- 16:24 CST：调度 runner 补齐后重新完成最终复核：`go test ./...`、`go vet ./...`、`go build ./cmd/team-cloud-server`、Kubernetes YAML parse 和 `git diff --check -- team_cloud_go teamDoc` 均通过。
- 16:42 CST：二次 GA 审计发现 Go 服务未覆盖 release manual 中 PostgreSQL/pgvector embedding 检索承诺；新增 GTC-22/GTC-23。
- 16:49 CST：按 TDD 增加 embedding 召回排序测试和 schema pgvector 测试，先确认失败，再实现 memory embedding、`query_embedding`、pgvector schema 和 cosine 排序；局部测试通过。
- 16:58 CST：GTC-22 后重新运行 `go test ./...`、`go vet ./...`、`go build ./cmd/team-cloud-server`、Kubernetes YAML parse 和 `git diff --check -- team_cloud_go teamDoc`，验证通过后关闭 GTC-23。
- 16:08 CST：完成 GTC-21 最终复核：`go test ./...`、`go vet ./...`、`go build ./cmd/team-cloud-server`、Kubernetes YAML parse 和 `git diff --check -- team_cloud_go teamDoc` 均通过。
