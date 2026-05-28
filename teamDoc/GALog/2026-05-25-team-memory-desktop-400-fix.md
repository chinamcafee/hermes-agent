# Team Memory Desktop 400 修复记录

## 背景

用户分别在 Hermes CLI 和 Hermes Desktop 中输入自然语言指令：

`新增一个团队记忆：公司是2016年成立的`

CLI 最终返回团队记忆创建成功，Desktop 返回本地个人记忆写入成功，但 Team Memory 返回 400。

## 根因

排查 `~/.hermes/state.db` 中失败会话后确认，Desktop 路径并非 IPC 或 Team Cloud URL 配置错误，而是模型在工具调用中生成了 Team Cloud schema 不接受的可选字段：

- `memory_type=company_info` / `general`
- `sensitivity=public` / `internal`

Team Cloud PostgreSQL schema 只允许 `sensitivity` 为：

- `normal`
- `pii`
- `secret`
- `restricted`

CLI 成功是因为同一模型后续重试时省略了可选字段，Hermes Agent 适配器默认补齐为 `memory_type=fact`、`sensitivity=normal`，因此创建成功。

## 修复

本次修复收敛在 Hermes Agent 的 Team Memory provider：

- 对 `team_memory_add` 和 `team_memory_propose` 的 `memory_type` 做白名单归一化。
- 对 `sensitivity` 做白名单归一化，未知值统一降级为 `normal`。
- 在工具 schema 中为 `memory_type` 和 `sensitivity` 增加 enum，减少模型生成非法值。
- 强化 system prompt：显式团队记忆请求必须使用 `team_memory_add`，不得使用 `team_memory_propose`，也不得回退到本地个人记忆。

## 验证

运行：

```bash
./scripts/run_tests.sh tests/hermes_cli/test_team_memory_provider_tools.py tests/hermes_cli/test_team_memory_provider.py tests/run_agent/test_memory_provider_init.py
```

结果：

- 18 tests passed
- 0 failed

