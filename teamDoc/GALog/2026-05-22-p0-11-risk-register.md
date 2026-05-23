# GALog 2026-05-22 P0-11 风险登记册

## 工作粒度

- 工作包：`P0-11 风险登记册`
- 类型：项目统筹 / 风险治理
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/08-risks-and-validation.md`
- `teamDoc/GADoc/P0-04-component-version-license-freeze.md`
- `teamDoc/GADoc/P0-07-spicedb-schema-v0.md`
- `teamDoc/GADoc/P0-08-postgres-pgvector-schema-v0.md`
- `teamDoc/GADoc/P0-09-minio-backup-model-v0.md`
- `teamDoc/GADoc/P0-10-ga-acceptance-matrix.md`

## 产出

- 新增：`teamDoc/GADoc/artifacts/risk-register-v0.csv`
- 新增：`teamDoc/GADoc/P0-11-risk-register.md`

## 执行记录

1. 汇总 P0-04 到 P0-10 过程中出现的许可证、供应链、权限、一致性、性能、runtime、工具和备份恢复风险。
2. 为每条风险登记 impact、probability、severity、owner、mitigation、trigger、status。
3. 将 Critical 风险与 GA 验收矩阵 blocker 对齐。
4. 明确 Critical 风险不能未经 scope 修改进入 GA。

## 决策摘要

1. v0 风险登记册包含 12 条风险。
2. MinIO AGPL、SpiceDB 一致性、memory 隔离、identity header spoofing、工具权限绕过是 Critical 跟踪重点。
3. psycopg LGPL 被登记为 dependency 风险，但默认路线继续使用 asyncpg。

## 验证计划

- 校验 CSV 可解析。
- 检查风险登记册包含 MinIO AGPL、SpiceDB 一致性、pgvector 性能、Hermes core patch。
- 检查 Markdown 文档列出风险状态规则和 GA 约束。
- 验证后更新 `progress-tracker.md` 中 `P0-11` 为 `Done`。

## 验证结果

```text
rows=12
severity=Critical:7,High:4,Medium:1
status=Open:12
```

## 后续

- 进入 `P0-12 交付基线计划`。
