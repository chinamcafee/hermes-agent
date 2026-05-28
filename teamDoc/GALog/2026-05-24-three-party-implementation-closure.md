# 2026-05-24 三方团队能力实现收口日志

## 背景

用户确认 Python 版 `team_cloud` 已删除，Go 服务端目录重命名为 `team_cloud`，并要求完成 CLI、Desktop 与 Team Cloud 的团队父人格、云备份和团队记忆边界实现。

## 本轮完成

- Go `team_cloud` 增加团队父人格 API、Store 和测试，并由 Dashboard 提供“团队父人格”治理入口。
- Hermes CLI 以 `/cloud-backup` 替换 `/memory-backup`，支持 memory 与 soul 分资源备份。
- Hermes Agent 保存本地人格时，在 team mode 下尝试调用当前模型供应商做团队父人格和本地人格合并；未配置或不可用时返回优雅失败并使用安全降级组合。
- Team Cloud 退役个人记忆外部管理路径：拒绝 `scope=personal`，prefetch 只返回团队记忆，个人备份 API 不再注册。
- `plugins/team_policy` 改为引用 `agent.team_tool_policy`，并补齐 fail-closed hook。
- `scripts/team-cloud-spicedb-schema-ci.sh` 不再调用已删除的 Python `team_cloud.authz.schema_ci`。

## 验证

- `cd team_cloud && go test ./...`：通过。
- `venv/bin/python -m pytest tests/hermes_cli/test_cloud_backup_cli.py tests/hermes_cli/test_team_cloud_cli.py tests/hermes_cli/test_team_soul.py tests/hermes_cli/test_team_tool_policy.py tests/hermes_cli/test_team_memory_provider.py tests/hermes_cli/test_team_memory_provider_tools.py tests/run_agent/test_memory_provider_init.py tests/run_agent/test_team_soul_runtime.py -q`：37 passed。
- `scripts/team-cloud-spicedb-schema-ci.sh --static-only`：通过。
