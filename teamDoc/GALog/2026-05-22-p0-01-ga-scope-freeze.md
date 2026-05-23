# GALog 2026-05-22 P0-01 GA 范围冻结

## 工作粒度

- 工作包：`P0-01 GA 范围冻结`
- 类型：项目统筹 / 架构范围冻结
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/README.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/04-memory-design.md`
- `teamDoc/12-ga-product-requirements.md`
- `teamDoc/15-minio-personal-backup.md`
- `teamDoc/16-ga-test-release-checklist.md`
- `teamDoc/GAStep/01-work-package-register.md`
- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`

## 决策摘要

1. GA 范围固定为 `Casdoor + SpiceDB + PostgreSQL/pgvector + MinIO + Team Cloud + Hermes runtime`。
2. GA 必须覆盖企业身份、资源授权、双层记忆、个人记忆定时备份、工具治理、管理 API/Web、部署发布和反向安全验收。
3. Beta 只允许裁剪部署广度、体验完整度、权限解释深度和性能调优成熟度，不允许裁剪安全边界和备份恢复闭环。
4. 明确排除本地 Dashboard token 充当团队登录、数据库 ACL 替代 SpiceDB、第三方 memory provider 作为 canonical memory、管理员静默下载个人备份等路径。

## 产出

- 新增：`teamDoc/GADoc/P0-01-ga-scope-freeze.md`

## 验证计划

- 检查决策文档存在且包含 GA 必须项、Beta 可缺项、明确不做项、裁剪规则。
- 检查 `progress-tracker.md` 中 `P0-01` 状态在验证后更新为 `Done`。

## 后续

- 严格进入 `P0-02 代码边界审计`，审计 Hermes core、plugin、Gateway、API server、memory provider 和 hook 改动点。
