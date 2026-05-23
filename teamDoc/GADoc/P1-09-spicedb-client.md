# P1-09 SpiceDB client

日期：2026-05-22
状态：Implemented
前置：`P1-03 本地 compose 栈`、`P0-07 SpiceDB schema v0`

## 目标

本步骤实现 Team Cloud 的 AuthzClient 抽象层，固定产品动作名到 SpiceDB schema permission 名的映射，并提供 check、batch check、lookup resources、write relationships 四类调用接口。真实 `authzed` SDK transport 留给后续接入，当前先使用 transport 协议保持可测试和可替换。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/authz/spicedb.py` | SpiceDB ref、relationship、permission mapping 和 client。 |
| `team_cloud/authz/__init__.py` | AuthZ primitives 包导出。 |
| `tests/team_cloud/test_spicedb_client.py` | mapping、check、batch、lookup、relationship format、fail-closed 测试。 |

## 行为

- `SubjectRef` 支持 `user` 和 `service_account`。
- `ResourceRef` 使用 `resource_type:id` 格式。
- `Relationship` 输出 `resource#relation@subject`。
- `permission_for_action()` 将产品动作映射为 schema permission，例如：
  - `memory.personal.read` -> `memory#read_personal`
  - `memory.team.read` -> `memory#read_team`
  - `tool.terminal.execute` -> `tool#terminal_execute`
  - `chat.run` -> `project#run_agent` 或 `session#run`
- `SpiceDBClient.check()` 默认 fail closed：transport 异常返回 deny，reason 为 `spicedb_error`。
- `batch_check()` 保持输入顺序返回决策。
- `lookup_resources()` 在 transport 异常时返回空集合，避免错误放大为越权。
- `write_relationships()` 接收 typed relationships 并格式化为 SpiceDB relationship string。

## 非目标

- 不引入 `authzed` Python SDK。
- 不直接连接本地 compose 中的 SpiceDB。
- 不实现 relationship outbox worker。
- 不实现 schema CI。
- 不实现 permission explain path。

## 后续衔接

- P1-10：基于 P0-07 validation fixture 实现 schema CI。
- P1-11：relationship outbox 调用 `write_relationships()`。
- P1-12：AuthZ middleware 调用 `check()` 并把异常路径保持 fail closed。
- P1-18/P3-15：Permission Explorer 在该 client 上扩展 explain 能力。
