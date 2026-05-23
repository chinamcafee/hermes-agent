# P1-10 SpiceDB schema CI

日期：2026-05-22
状态：Implemented
前置：`P0-07 SpiceDB schema v0`

## 目标

本步骤为 P0-07 的 SpiceDB schema 和 validation fixture 增加可重复运行的 CI 封装。当前实现包含两层校验：不依赖 Docker/zed 的静态校验，以及用于 CI 或本地 Docker 环境的 pinned `zed validate` 命令。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/schema_ci.py` | schema/fixture 静态校验、产品 permission mapping 校验、zed 命令生成。 |
| `scripts/team-cloud-spicedb-schema-ci.sh` | 本地/CI 入口，支持 `--static-only`、`--print-zed-command`、`--run-zed`。 |
| `tests/team_cloud/test_spicedb_schema_ci.py` | 静态校验、mapping、命令和脚本入口测试。 |

## 行为

- 静态校验：
  - 确认 validation fixture 的 `schemaFile` 指向 `schema-v0.zed`。
  - 解析 schema 中的 `definition` 和 `permission`。
  - 校验 `assertTrue` 与 `assertFalse` 均存在。
  - 校验 fixture 断言引用的 resource permission 在 schema 中存在。
  - 校验 P1-09 `PRODUCT_PERMISSION_MAP` 中的 permission 在 schema 中存在。
- zed 命令：
  - 使用 pinned image `authzed/zed:v1.1.1`。
  - 挂载 `teamDoc/GADoc/artifacts/spicedb` 为 `/work`。
  - 执行 `zed validate --type yaml schema-v0-validation.yaml`。
- 脚本入口：
  - 默认 `--static-only`。
  - 优先使用 `$PYTHON`、`.venv/bin/python`、`venv/bin/python`，最后回退系统 `python`。

## 非目标

- 不在测试中强制运行 Docker。
- 不启动 compose SpiceDB。
- 不实现 permission integration e2e。
- 不实现 relationship outbox。

## 后续衔接

- P1-11：relationship outbox 写入后可复用 schema 关系格式校验。
- P1-12/P1-19：API AuthZ 集成测试使用同一 permission mapping。
- P4/P5：CI 中可将 `scripts/team-cloud-spicedb-schema-ci.sh --run-zed` 纳入发布门禁。
