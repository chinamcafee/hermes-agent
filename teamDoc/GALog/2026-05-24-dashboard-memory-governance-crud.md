# 2026-05-24 Dashboard 记忆治理 CRUD 日志

## 需求

记忆治理页需要覆盖：

- 自动抽取团队记忆列表。
- 管理员创建团队记忆入口。
- 编辑任意已有团队记忆。
- 停用记忆但不删除。
- 彻底删除记忆。

同时，团队记忆需要通过标签区分来源：

- `auto_extracted`：来源于团队成员客户端中的个人记忆抽取。
- `admin_created`：来源于管理员在 Dashboard 中直接创建。

## 设计收敛

- 第一版继续使用单团队空间模型，不引入工作组。
- `team_shared` 作为团队记忆唯一 scope。
- `source_member_id` 记录自动抽取来源成员。
- `created_by_member_id` 记录管理员创建者。
- `POST /v1/memory/{id}/disable` 作为停用语义，落库状态为 `archived`。
- `DELETE /v1/memory/{id}` 从软删除改为硬删除。

## 修改记录

- `store.MemoryItem` 新增 `source_type`、`source_member_id`、`created_by_member_id`。
- 内存 store 和 PostgreSQL store 持久化来源字段。
- PostgreSQL schema 为 `tcg_memory_items` 增加来源字段和迁移列。
- `Backend` contract 新增 `DeleteMemory`。
- HTTP API 增加 `disable` action，`DELETE /v1/memory/{id}` 改为硬删除。
- Dashboard client 新增 `listTeamMemories`、`createTeamMemory`、`updateMemory`、`disableMemory`、`deleteMemory`。
- Dashboard “记忆治理”页升级为团队记忆库工作台，包含统计卡片、来源标签、创建表单、编辑表单、停用和硬删除操作。
- 交互补强：Dashboard “记忆治理”页改为列表优先，不再在 Tab 首屏堆叠创建、编辑、审核表单；创建、编辑和审核操作进入弹窗流程。

## TDD 记录

先写失败测试：

```bash
cd team_cloud
go test ./internal/httpapi -run TestTeamMemoryGovernanceLifecycleSourcesAndHardDelete -count=1

cd dashboard
npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx
```

红灯结果：

- 后端测试失败于缺少 `source_type/source_member_id`。
- Dashboard client 测试失败于 `listTeamMemories is not a function`。
- Dashboard 页面测试失败于缺少“团队记忆库”工作台。

实现后转绿：

```bash
cd team_cloud
go test ./internal/httpapi -run TestTeamMemoryGovernanceLifecycleSourcesAndHardDelete -count=1
go test ./...

cd dashboard
npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx
npm run type-check
```

## 最终验证

已运行：

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
python -m json.tool teamDoc/GADoc/artifacts/release/team-cloud-api-docs-v0.json >/dev/null
git diff --check -- team_cloud teamDoc
```

结果：上述命令均通过。
