# GTC-81 到 GTC-85 三方团队能力实现收口

日期：2026-05-24

## 范围

本轮把此前仅完成规划的三方团队能力落成代码，并收敛 Go 版 `team_cloud/` 的职责边界：

- Hermes CLI 以 `/cloud-backup memory|soul` 作为唯一备份入口，旧 `/memory-backup` 不保留兼容。
- Team Cloud 只管理团队记忆和团队父人格，不再对外管理个人记忆或个人备份。
- Team Cloud Dashboard 新增团队父人格治理页面，编辑操作放入弹窗式工作流。
- Hermes Agent 在 team mode 下保存本地人格时，调用当前 profile 的模型供应商合并团队父人格和本地人格。
- 旧 `team_cloud` 运行时引用迁移到 `agent/` 或当前 Go `team_cloud/`，脚本不再调用已删除服务端包。

## 实现记录

| 项目 | 实现 |
| --- | --- |
| 本地备份 | `hermes_cli/cloud_backup.py` 支持 memory/soul 两类资源的配置、周期、备份、历史和恢复。 |
| 团队父人格 | `team_cloud/internal/httpapi/server.go` 暴露 `/v1/team-soul` 和 `/v1/runtime/team-soul`；Dashboard 提供只读摘要和弹窗编辑。 |
| effective soul | `hermes_cli/team_soul.py` 读取团队父人格、本地 `SOUL.md`，配置模型供应商时调用 auxiliary LLM 合并；失败时保存不回滚并使用安全降级组合。 |
| 运行时注入 | `agent/system_prompt.py` 在 team mode 下优先注入 effective soul，local mode 保持本地 `SOUL.md`。 |
| 团队记忆边界 | Go Store schema 和 HTTP guard 只接受 `scope=team_shared`，prefetch 即使收到 `include_personal=true` 也只返回团队记忆。 |
| 个人备份退役 | `/v1/me/memory-backup-policy`、`/v1/backups/personal/*` 不再注册路由；Backend 接口移除个人备份/恢复方法。 |
| 工具权限插件 | `agent/team_tool_policy.py` 接管 Team Tool Policy fail-closed hook contract。 |
| 脚本收口 | `scripts/team-cloud-smoke.sh`、`scripts/team-cloud-secrets.sh`、`scripts/team-cloud-offline-bundle.sh` 均改为围绕当前 Go `team_cloud/` 工作，不再引用旧 deploy compose/Helm/offline 资产。 |
| Desktop 验证 | GTC-86 已完成主会话验证：Desktop Bridge/Soul/Cloud Backup 只消费 Hermes Agent Bridge，不直连 Team Cloud。 |
| Bridge profile scoping | GTC-88 补齐 Hermes Agent Bridge 的 `profile` query 生效逻辑，避免 Desktop 多 profile 场景误读写默认 profile。 |

## 验证

- `cd team_cloud && go test ./...`
- `venv/bin/python -m pytest tests/hermes_cli/test_cloud_backup_cli.py tests/hermes_cli/test_team_cloud_cli.py tests/hermes_cli/test_team_soul.py tests/hermes_cli/test_team_tool_policy.py tests/hermes_cli/test_team_memory_provider.py tests/hermes_cli/test_team_memory_provider_tools.py tests/run_agent/test_memory_provider_init.py tests/run_agent/test_team_soul_runtime.py -q`
- `scripts/team-cloud-spicedb-schema-ci.sh --static-only`

Dashboard 侧验证由 Dashboard 子任务执行：

- `cd team_cloud/dashboard && npm test -- --run`
- `cd team_cloud/dashboard && npm run type-check`
- `cd team_cloud/dashboard && npm run build`
