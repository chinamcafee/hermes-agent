# GALog 2026-05-22 P0-10 GA 验收矩阵

## 工作粒度

- 工作包：`P0-10 GA 验收矩阵`
- 类型：项目统筹 / 验收治理
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/08-risks-and-validation.md`
- `teamDoc/12-ga-product-requirements.md`
- `teamDoc/16-ga-test-release-checklist.md`
- `teamDoc/GADoc/P0-01-ga-scope-freeze.md`
- `teamDoc/GADoc/P0-07-spicedb-schema-v0.md`
- `teamDoc/GADoc/P0-08-postgres-pgvector-schema-v0.md`
- `teamDoc/GADoc/P0-09-minio-backup-model-v0.md`

## 产出

- 新增：`teamDoc/GADoc/artifacts/ga-acceptance-matrix-v0.csv`
- 新增：`teamDoc/GADoc/P0-10-ga-acceptance-matrix.md`

## 执行记录

1. 核对 P0-10 要求：安全、性能、备份恢复、发布、文档。
2. 将现有风险验证计划和 GA 产品验收口径合并为可追踪 CSV。
3. 为每个验收项指定 domain、criterion、evidence、owner、phase 和 `ga_blocking`。
4. 明确跨租户/跨成员泄漏、工具越权、审计缺失、SBOM/许可证/Runbook 缺失为 GA blocker。

## 决策摘要

1. v0 矩阵包含 32 个验收项、7 个验收域。
2. 30 个验收项阻断 GA；2 个性能/离线包相关项目可在明确风险下进入 Post-GA backlog。
3. P4 Beta Exit 和 P5 GA Sign-off 必须引用同一矩阵，避免验收口径漂移。

## 验证计划

- 校验 CSV 可解析。
- 检查矩阵覆盖安全、性能、备份恢复、发布、文档。
- 检查 Markdown 文档列出 blocker 规则、证据要求和后续约束。
- 验证后更新 `progress-tracker.md` 中 `P0-10` 为 `Done`。

## 验证结果

```text
rows=32
domains=7 ['BackupRestore', 'Documentation', 'Performance', 'Pilot', 'Release', 'Security', 'Signoff']
blocking=30
```

## 后续

- 进入 `P0-11 风险登记册`。
