# GTC-22 Go pgvector 记忆检索闭环

日期：2026-05-23

## 背景

二次 GA 审计发现，release manual 仍承诺 PostgreSQL/pgvector 团队记忆存储与检索，但 Go 服务端只按内容字符串匹配召回。该差异会让 Go 版服务端无法满足原 GA 技术规划。

## 实现结果

- `store.MemoryItem` 新增 `embedding` 字段。
- `/v1/memory` create/update 支持 `embedding` 数组。
- `/v1/memory/prefetch` 支持 `query_embedding` 数组。
- 内存后端按 cosine similarity 对候选 memory 排序，作为单元测试和开发模式语义。
- PostgreSQL schema 新增 `create extension if not exists vector`、`tcg_memory_items.embedding vector(1536)` 和 HNSW cosine index。
- PostgreSQL store 对 memory embedding 进行读写和 restore 保留，prefetch 共享同一排序逻辑。

## 验证证据

- `go test ./internal/httpapi ./internal/store/postgres ./internal/store/memory ./internal/store`
- `cd team_cloud_go && go test ./...`
- `cd team_cloud_go && go vet ./...`
- `cd team_cloud_go && go build ./cmd/team-cloud-server`
- Kubernetes YAML parse：`kubernetes yaml ok: Secret,Deployment,Service`
- `git diff --check -- team_cloud_go teamDoc`
- 红灯证据：新增测试前，`TestMemoryPrefetchRanksByQueryEmbedding` 返回 ID 顺序而非 embedding 相似度顺序；schema test 缺少 vector extension。
- 绿灯证据：实现后，上述局部测试通过。
