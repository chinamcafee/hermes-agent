# P3-01 工具风险 taxonomy

日期：2026-05-22
状态：Implemented
前置：`P2-14 AIAgent.team_context`

## 目标

本步骤建立 Team Cloud 工具权限硬化的基础分类：safe/network/file/terminal/destructive/secret。P3-01 只产出 taxonomy、分类函数和 artifact，不在本步骤拦截工具调用；P3-02 TeamToolPolicyHook 负责把分类接入 `pre_tool_call` enforcement。

## 工件

| 工件 | 用途 |
| --- | --- |
| `team_cloud/tool_risk.py` | 工具风险分类函数、审批门槛和 taxonomy builder。 |
| `teamDoc/GADoc/artifacts/tool-risk-taxonomy-v0.json` | 可审计 taxonomy artifact。 |
| `tests/team_cloud/test_tool_risk_taxonomy.py` | taxonomy、artifact、文档和 smoke 登记测试。 |

## 分类

| 分类 | 含义 | 默认是否需要审批 |
| --- | --- | --- |
| `safe` | 本地只读上下文、任务状态、无外发副作用。 | 否 |
| `network` | 网络请求、浏览器、消息发送或外部服务查询。 | 否，P3-02 可按 org policy 升级。 |
| `file` | 本地文件读取、写入、patch、生成图片或音频文件。 | 否，P3-02 可按路径 policy 升级。 |
| `terminal` | shell/process/code execution/delegation/cron/computer use。 | 是 |
| `destructive` | 删除、系统级命令、Home Assistant service call 等高影响动作。 | 是 |
| `secret` | 参数 key 暴露 token/password/secret/credential/private_key/api_key。 | 是 |

## 映射和升级规则

- `classify_tool_call(tool_name, args)` 先扫描 secret-like argument key，命中即升级到 `secret`。
- `terminal` 的 `command` 或 `cmd` 命中 `rm -r`、`sudo`、`dd if=`、`mkfs`、`diskutil`、`drop table`、`truncate table` 时升级到 `destructive`。
- 未登记工具默认 `safe`，避免 P3-01 误拦截；P3-02 hook 必须记录 unknown tool 并允许 org policy 覆盖。
- `risk_requires_approval()` 对 `terminal`、`destructive`、`secret` 返回 true。

## P3 衔接

- P3-02 TeamToolPolicyHook 使用 `classify_tool_call()` 作为默认风险输入，然后查询 SpiceDB/org policy。
- P3-03 高危工具审批使用 `risk_requires_approval()` 的结果触发 approval flow。
- P3-04 Tool audit 把分类结果写入 `cloud_tool_calls.risk_level`；如果数据库枚举继续沿用 `file_read/file_write`，P3-04 需要做兼容映射。

## 验证

```bash
scripts/run_tests.sh tests/team_cloud/test_tool_risk_taxonomy.py
venv/bin/ruff check team_cloud/tool_risk.py tests/team_cloud/test_tool_risk_taxonomy.py
venv/bin/python -m py_compile team_cloud/tool_risk.py tests/team_cloud/test_tool_risk_taxonomy.py
venv/bin/python -m json.tool teamDoc/GADoc/artifacts/tool-risk-taxonomy-v0.json
scripts/team-cloud-foundation-smoke.sh
```
