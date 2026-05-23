# 06. Team Cloud Go 服务端重写步骤

本文件是 GA 后新增需求的补充任务拆解。由于 Python `team_cloud/` 从未上线部署，Go 版允许破坏性更新并作为首次上线服务端；迁移期间不修改 `team_cloud/` 目录。

## 执行原则

- `team_cloud_go/` 是独立 Go module，未来云端部署默认使用该目录构建镜像。
- Python `team_cloud/` 只作为参考实现，不再作为 GA 部署目标。
- 生产环境必须使用 PostgreSQL 后端；内存后端仅用于开发和单元测试。
- HTTP API 默认启动即暴露团队管理、双层记忆、review queue 和个人备份策略能力。
- Kubernetes manifest 必须包含 readiness/liveness probe、非 root 运行、只读根文件系统和 Secret 注入。

## 工作包

| ID | 工作包 | 主要产出 | 前置 | 状态 |
| --- | --- | --- | --- | --- |
| GTC-01 | Go 重写范围冻结 | 明确 Python `team_cloud/` 不再作为上线服务端，新增 Go module 边界 | P5 | Done |
| GTC-02 | Go module 和 HTTP 框架 | `team_cloud_go/go.mod`、`cmd/team-cloud-server`、`internal/httpapi` | GTC-01 | Done |
| GTC-03 | 服务 token 和健康检查 | `/healthz`、`/readyz`、`/metrics`、Bearer/Header token 鉴权 | GTC-02 | Done |
| GTC-04 | 组织/团队/成员 API | organization、team、member invite/list/disable API | GTC-03 | Done |
| GTC-05 | 双层记忆 API | personal/team_shared CRUD、prefetch、observation、review approve/reject | GTC-04 | Done |
| GTC-06 | 个人记忆备份策略 API | `/v1/me/memory-backup-policy` 查询和更新 | GTC-05 | Done |
| GTC-07 | PostgreSQL 持久化后端 | `internal/store/postgres`、启动自动 migration、readyz backend ping | GTC-05 | Done |
| GTC-08 | 容器和 Kubernetes 资产 | `Dockerfile`、`deploy/kubernetes/team-cloud-go.yaml` | GTC-07 | Done |
| GTC-09 | 技术文档更新 | `teamDoc` README、技术设计、backlog、release manual | GTC-08 | Done |
| GTC-10 | 验证和 GA 复核 | `go test ./...`、`go vet ./...`、manifest 检查 | GTC-09 | Done |
| GTC-11 | Casdoor 风格 JWT 鉴权 | RS256/JWKS issuer、audience、expiration 校验 | GTC-03 | Done |
| GTC-12 | 授权关系和权限检查 API | relationship write、permission check、解释路径 | GTC-04 | Done |
| GTC-13 | Audit 事件 API | 关键管理、记忆、备份、删除、工具策略操作留痕 | GTC-04 | Done |
| GTC-14 | 个人备份恢复 API | backup run、restore preview、restore execute、checksum | GTC-06 | Done |
| GTC-15 | 组织导出和删除请求 API | org export 不含 personal memory、personal deletion execute | GTC-14 | Done |
| GTC-16 | 工具策略和 runtime 事件 API | tool risk evaluation、approval_required、session/runtime event bridge | GTC-13 | Done |
| GTC-17 | PostgreSQL schema 扩展 | audit、relationship、backup、export、deletion、tool、session、runtime 表 | GTC-16 | Done |
| GTC-18 | 远程 SpiceDB/Authzed 授权适配 | 可配置 HTTP adapter、relationship write、permission check、fail-closed readiness | GTC-12 | Done |
| GTC-19 | JWT 业务 API 授权闭环 | org/member scope 防伪造、高风险 API 授权、team_shared read_team 过滤 | GTC-18 | Done |
| GTC-20 | 加密备份对象和恢复守卫 | AES-GCM JSONL、S3/MinIO upload、object manifest、scheduled policy runner、preview-before-execute | GTC-14 | Done |
| GTC-21 | Go 服务 GA 最终复核 | 代码验证、manifest 验证、文档一致性和 release manual 收口 | GTC-20 | Done |
| GTC-22 | pgvector 记忆检索闭环 | PostgreSQL pgvector schema、memory embedding 字段、query_embedding 排序召回 | GTC-05 | Done |
| GTC-23 | Go 服务二次 GA 复核 | GTC-22 后重新运行测试、vet、build、manifest 和文档一致性检查 | GTC-22 | Done |
| GTC-24 | 高风险治理 API 授权硬化 | authz relationship、audit、review、backup detail、deletion execute、runtime event、org list 的 JWT 业务授权闭环 | GTC-23 | Done |
| GTC-25 | 对象存储恢复闭环 | S3/MinIO Get、checksum 校验、AES-GCM JSONL 解密、restore preview/execute 读取对象内容 | GTC-20 | Done |
| GTC-26 | PostgreSQL pgvector SQL 检索 | query_embedding 走 `embedding <=> $vector` SQL 排序和 HNSW 索引路径 | GTC-22 | Done |
| GTC-27 | Restore mode 执行语义 | merge、overwrite、archive_current_then_restore 三种恢复模式闭环 | GTC-14 | Done |
| GTC-28 | Backup cadence 和 retention 闭环 | policy last/next run、按 cadence 到期调度、retention_count 清理旧 job/object | GTC-20 | Done |
| GTC-29 | Go 服务最终 GA 复核 | GTC-24 到 GTC-28 后重新运行 test、vet、build、manifest、文档一致性检查 | GTC-28 | Done |

## 验收口径

- `cd team_cloud_go && go test ./...` 通过。
- `cd team_cloud_go && go vet ./...` 通过。
- `cd team_cloud_go && go build ./cmd/team-cloud-server` 通过。
- `team_cloud_go/deploy/kubernetes/team-cloud-go.yaml` YAML 解析通过。
- `TEAM_CLOUD_DATABASE_URL` 设置后服务使用 PostgreSQL 后端；为空时使用内存后端。
- K8s deployment 通过 Secret 注入 `TEAM_CLOUD_DATABASE_URL` 和 `TEAM_CLOUD_SERVICE_TOKEN`。
- K8s deployment 显式配置 `TEAM_CLOUD_CASDOOR_ISSUER`、`TEAM_CLOUD_CASDOOR_AUDIENCE` 和 `TEAM_CLOUD_CASDOOR_JWKS_URL`。
- 生产环境可通过 `TEAM_CLOUD_AUTHZ_MODE=spicedb_http` 使用远程 SpiceDB/Authzed compatible HTTP API；远程授权不可用时 readiness fail closed。
- JWT 业务请求必须绑定 `hermes_org_id` 和 `hermes_member_id`，禁止通过 payload/query 伪造其他 org/member。
- `team_shared` prefetch 必须经 `read_team` 授权过滤。
- PostgreSQL schema 必须包含 pgvector extension、memory embedding 字段和向量索引；prefetch 必须支持 `query_embedding` 语义排序。
- 生产环境可通过 `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 上传 AES-GCM 加密 JSONL 到 S3/MinIO，并写入 backup object manifest；服务端调度器会扫描 enabled policy；restore execute 必须先完成 restore preview。
- 高风险治理 API 必须先按资源归属取数，再使用 JWT principal 和 SpiceDB/Authzed 权限判断；不得信任请求体中的 org/member/actor 字段完成授权。
- 对象存储模式下 restore preview/execute 必须读取并校验 S3/MinIO 加密对象，数据库 snapshot 只能作为缓存。
- PostgreSQL 后端提供 query embedding 时必须使用 pgvector SQL 排序路径，不能只在应用层排序。
- backup scheduler 必须尊重 cadence 和 retention_count。
- release manual 明确 Go 版服务端是 Team Cloud 首次上线部署目标。

## GA 收口结果

- GTC-18 到 GTC-20 已补齐远程授权、业务授权和加密备份对象路径。实现口径采用 Go 1.24 兼容的标准库 HTTP/S3 adapter，不引入会提升 toolchain 的 SDK 依赖。
- GTC-22 补齐 Go 服务端 pgvector/embedding 检索闭环，避免 release manual 中 PostgreSQL/pgvector 承诺与实现不一致。
- GTC-23 已完成 GTC-22 后的二次最终验证，Go 服务端达到本轮 GA 状态。
- GTC-24 到 GTC-28 已补齐二次 GA 复核发现的阻塞硬化项，覆盖治理 API 授权、对象存储恢复、pgvector SQL 检索、restore mode、backup cadence/retention。
- GTC-29 已完成最终验证，Go 服务端达到本轮 GA 状态。
