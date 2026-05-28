# GTC-79 `/memory-backup` 破坏性删除规划

日期：2026-05-24

## 需求

用户明确允许破坏性更新。由于本团队项目尚未上线部署，旧 `/memory-backup` 入口不需要保留历史兼容，不需要隐藏别名，也不需要迁移提示。

## 决策

- 唯一备份入口是 `/cloud-backup` 和 `hermes cloud-backup`。
- `/cloud-backup memory ...` 负责个人记忆备份、历史、恢复和调度。
- `/cloud-backup soul ...` 负责本地 `SOUL.md` 备份、历史、恢复和调度。
- `/memory-backup` slash command 必须删除。
- `hermes memory-backup` 顶层 CLI subcommand 必须删除。
- `memory_backup` 配置键必须删除，统一使用 `cloud_backup`。
- 旧测试文件应替换为 `tests/hermes_cli/test_cloud_backup_cli.py`。

## 后续编码删除清单

- 删除或改造 `hermes_cli/memory_backup.py` 的对外命令入口。
- 移除 `hermes_cli/commands.py` 中的 `memory-backup` command definition。
- 移除 `cli.py` 中 `/memory-backup` dispatch、help 和状态展示。
- 移除 `hermes_cli/main.py` 中 `memory-backup` argparse subcommand。
- 移除 `hermes_cli/config.py`、`cli.py` 默认配置中的 `memory_backup`。
- 移除 cron job 名称和脚本中 `memory-backup` 命名，改为 resource-specific `cloud-backup-memory`。
- 删除或重命名 `tests/hermes_cli/test_memory_backup_cli.py`。
- 更新 Desktop UI，不调用 `hermes memory-backup ...`。

## 验收

- `rg "memory-backup|/memory-backup|memory_backup" hermes_cli cli.py tests ui-tui tui_gateway teamDoc/releaseManual` 不再出现作为可用入口的文案。
- `/help` 不显示 `/memory-backup`。
- `hermes --help` 不显示 `memory-backup`。
- `/cloud-backup memory backup` 和 `/cloud-backup soul backup` 分别可用。
- memory/soul restore 会校验 resource type，不能交叉恢复。
