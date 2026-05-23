# GALog 2026-05-22 P0-07 SpiceDB schema v0

## 工作粒度

- 工作包：`P0-07 SpiceDB schema v0`
- 类型：授权模型 / 可验证 schema 工件
- 执行日期：2026-05-22
- 执行者：Codex

## 输入依据

- `teamDoc/GAStep/02-phase-0-1-foundation-steps.md`
- `teamDoc/05-auth-permission-design.md`
- `teamDoc/13-casdoor-spicedb-integration.md`
- `teamDoc/GADoc/adr/ADR-0002-spicedb-authorization.md`
- `teamDoc/GADoc/P0-05-local-topology-design.md`

## 产出

- 新增：`teamDoc/GADoc/artifacts/spicedb/schema-v0.zed`
- 新增：`teamDoc/GADoc/artifacts/spicedb/schema-v0-validation.yaml`
- 新增：`teamDoc/GADoc/P0-07-spicedb-schema-v0.md`

## 执行记录

1. 核对 P0-07 要求：schema 必须覆盖 organization/team/project/session/memory/document/tool/backup。
2. 基于现有权限设计草案扩展 service account、tool risk、backup owner-only read 和 break-glass 显式关系。
3. 为 schema 增加 validation fixture，覆盖正向和 deny case。
4. 拉取 `authzed/zed:v1.1.1` 用于本地 validation。

## 决策摘要

1. schema v0 使用 `user` 和 `service_account` 两类 subject。
2. 产品动作名继续可用，但 API 层映射到 SpiceDB 下划线 permission 名。
3. 个人记忆与个人备份默认 owner-only；管理员读个人备份必须走 break-glass workflow。
4. 工具权限拆成 safe/network/file_read/file_write/terminal/destructive 六档执行权限。
5. Break-glass 的“双人且限时”不放进 SpiceDB v0 表达，交由 Team Cloud workflow、关系时效和 audit 强制。

## 验证计划

- 运行 `zed validate --type yaml schema-v0-validation.yaml`。
- 检查 schema 文件包含 P0-07 指定的八类资源。
- 验证后更新 `progress-tracker.md` 中 `P0-07` 为 `Done`。

## 验证结果

```text
docker run --rm -v "$PWD/teamDoc/GADoc/artifacts/spicedb:/work" -w /work authzed/zed:v1.1.1 validate --type yaml schema-v0-validation.yaml
Success! - 37 relationships loaded, 22 assertions run, 0 expected relations validated
```

## 后续

- 进入 `P0-08 PostgreSQL/pgvector schema v0`。
