# 2026-05-24 Dashboard 记忆治理弹窗化操作流日志

## 需求

用户反馈“记忆治理”Tab 中创建、编辑、审核操作不应全部堆在同一个页面中，希望这些操作使用新页面或弹窗承载。

## 设计收敛

- 不新增路由，采用弹窗承载操作表单，保持管理台单页导航体验。
- Tab 默认视图只保留列表、统计、状态筛选和行级动作。
- 创建、编辑和审核都使用独立弹窗；停用和删除作为短动作保留在列表行内。
- 后端 API 不变，继续复用 GTC-66 的记忆治理接口。

## TDD 记录

先写失败测试：

```bash
cd team_cloud/dashboard
npm test -- --run src/app/page.test.tsx
```

红灯结果：

- 旧页面无法找到“新建团队记忆”按钮。
- 旧页面首屏存在“创建团队记忆”“编辑已选记忆”“审核操作”等常驻表单区。

实现后单测转绿：

```bash
cd team_cloud/dashboard
npm test -- --run src/app/page.test.tsx
```

## 修改记录

- `MemoryView` 新增 `MemoryDialog` 状态，统一管理 `create`、`edit`、`review` 三类弹窗。
- 团队记忆表格增加行级“编辑”“停用”“删除”动作。
- 待审队列从通用 `DataTable` 改为带“审核”行级动作的 `ReviewQueueTable`。
- 新增 `ModalShell`，统一弹窗标题、关闭按钮和 `role="dialog"` 语义。
- `globals.css` 新增弹窗、待审队列卡片和紧凑空状态样式。

## 最终验证

已运行：

```bash
cd team_cloud/dashboard
npm test -- --run src/lib/teamCloudClient.test.ts src/app/page.test.tsx
npm run type-check
npm run build

cd ../..
git diff --check -- team_cloud teamDoc
```

结果：上述命令均通过。
