# GALog 2026-05-22 P0-05 本地拓扑设计

## 工作粒度

- 工作包：`P0-05 本地拓扑设计`
- 类型：项目统筹 / 本地部署拓扑
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/03-target-architecture.md`
- `teamDoc/13-casdoor-spicedb-integration.md`
- `teamDoc/14-postgres-pgvector-memory-schema.md`
- `teamDoc/15-minio-personal-backup.md`
- `teamDoc/GADoc/P0-04-component-version-license-freeze.md`

## 产出

- 新增：`teamDoc/GADoc/P0-05-local-topology-design.md`

## 执行记录

1. 核对 `P0-05` 要求：端口、网络、volume、初始化数据、secret 注入、健康检查。
2. 确认当前仓库没有 `deploy/` 目录，P1 需要新建 `deploy/team-cloud/compose.yaml`。
3. 设计本地最小全栈：Team Web、Team API、Team Worker、Hermes Runtime、Casdoor、SpiceDB、PostgreSQL、MinIO、Mailpit。
4. 将本地 PostgreSQL 设计为单 service、多 database、多 role，以降低启动成本并保持生产可拆分。
5. 将 `latest` tag 禁用、secret 文件注入和 readiness gate 写入 P1 compose 约束。

## 决策摘要

1. 本地 host 入口端口固定为 `8781` Web、`8780` API、`18000` Casdoor、`19000/19001` MinIO、`54329` PostgreSQL、`50051` SpiceDB。
2. compose 网络拆为 `team-edge`、`team-control`、`team-data`。
3. canonical data 在 PostgreSQL 和 MinIO；Hermes runtime volume 不保存 canonical memory。
4. 初始化 jobs 必须幂等，重复执行不能产生重复组织、用户、bucket 或 relationship。
5. Health check 必须验证依赖可用性，`depends_on` 不能替代 readiness。

## 验证计划

- 检查拓扑文档包含端口、网络、volume、初始化数据、secret 注入、健康检查。
- 检查拓扑文档明确 P1 compose 路径和后续约束。
- 验证后更新 `progress-tracker.md` 中 `P0-05` 为 `Done`。

## 后续

- 进入 `P0-06 Casdoor OIDC 验证`。
