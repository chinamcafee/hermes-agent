# GTC-66 Dashboard 记忆治理 CRUD 和来源标签

日期：2026-05-24

## 背景

Dashboard V2 早期“记忆治理”页面只覆盖 review queue 的加载、批准和拒绝，无法直接管理已经进入团队记忆库的 `team_shared` 记忆。管理员也无法在页面中区分自动抽取的团队记忆和管理员主动创建的团队记忆。

本次升级将“记忆治理”扩展为团队记忆库工作台，覆盖列表、创建、编辑、停用和硬删除。

## 功能范围

- 展示团队成员客户端自动抽取的团队记忆列表。
- 支持管理员在 Dashboard 中直接创建团队记忆。
- 自动抽取记忆使用 `source_type=auto_extracted`，并记录 `source_member_id`。
- 管理员创建记忆使用 `source_type=admin_created`，并记录 `created_by_member_id`。
- 支持编辑任意团队记忆的内容、类型和敏感度。
- 支持停用团队记忆，停用使用 `status=archived`，不会删除数据。
- 支持彻底删除团队记忆，`DELETE /v1/memory/{id}` 改为硬删除，并级联移除关联 review item。

## 后端契约

`MemoryItem` 新增字段：

- `source_type`
- `source_member_id`
- `created_by_member_id`

API 行为：

- `GET /v1/memory?org_id=<org>&scope=team_shared&status=<status>`：返回团队记忆库列表和来源字段。
- `POST /v1/memory`：Dashboard 管理员创建时传入 `source_type=admin_created` 和 `status=active`。
- `PATCH /v1/memory/{id}`：编辑内容、`memory_type`、`sensitivity`，保留来源标签。
- `POST /v1/memory/{id}/disable`：停用记忆，写入 `status=archived`。
- `DELETE /v1/memory/{id}`：硬删除记忆。

鉴权仍沿用单团队空间模型：

- 团队记忆创建、编辑、停用和删除需要 `organization:{org_id}#write_team`。
- 团队记忆读取需要 `organization:{org_id}#read_team`，管理员拥有 `manage` 时可直接读取。

## Dashboard 信息架构

记忆治理页分为 3 个区域：

- 团队记忆库：列表、状态筛选、来源标签、选择操作。
- 记忆操作区：管理员创建和编辑通过弹窗完成，停用和硬删除作为列表行级动作。
- 待审队列：保留 review queue 的加载能力，批准和拒绝通过审核弹窗完成。

页面不再以“表单 + JSON 返回”为主，也不在 Tab 首屏堆叠多个表单；默认视图使用列表、统计卡片、行级动作和来源标签组织信息，创建、编辑、审核进入对话框。

## 验证

新增测试：

- `TestTeamMemoryGovernanceLifecycleSourcesAndHardDelete`
- `teamCloudClient.test.ts` 中的 team memory client contract
- `page.test.tsx` 中的完整记忆治理工作台渲染测试

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
