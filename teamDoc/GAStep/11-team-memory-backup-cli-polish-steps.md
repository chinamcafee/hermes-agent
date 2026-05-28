# 11. Team Memory Backup and CLI Polish Steps

本步骤文件覆盖 2026-05-24 追加需求：Team Cloud 云端只管理团队记忆；个人记忆备份回到 Hermes CLI 本地职责；Dashboard 的备份页面改为团队记忆备份管理；CLI 增加团队状态常驻提示和 Team Cloud API 熔断能力。

> GTC-77/GTC-79 后续更新：本步骤中的 `/memory-backup` 是历史实现阶段名称。新的权威主入口是 `/cloud-backup memory|soul`，并新增本地人格备份和团队父人格联动规划。由于项目尚未上线，后续编码直接删除 `/memory-backup`，不保留兼容别名或迁移提示。

| ID | 任务 | 状态 | 证据 |
| --- | --- | --- | --- |
| GTC-69 | 架构边界重写：MinIO 不再是 Team Cloud 必备组件，云端个人记忆备份退役 | Done | [GADoc](../GADoc/GTC-69-team-memory-backup-boundary.md), [GALog](../GALog/2026-05-24-team-memory-backup-cli-polish.md) |
| GTC-70 | Hermes CLI `/memory-backup` 历史入口退役：当前唯一入口是 `/cloud-backup memory|soul` | Done | `venv/bin/python -m pytest tests/hermes_cli/test_cloud_backup_cli.py tests/hermes_cli/test_team_cloud_cli.py tests/hermes_cli/test_team_memory_provider.py tests/hermes_cli/test_team_memory_provider_tools.py tests/run_agent/test_memory_provider_init.py -q` |
| GTC-71 | Hermes CLI Team Cloud 状态栏和 API 熔断/恢复控制 | Done | `tests/hermes_cli/test_team_cloud_cli.py`, `venv/bin/python -m py_compile hermes_cli/team_cloud.py cli.py` |
| GTC-72 | Team Cloud Go 团队记忆备份 API、历史列表、恢复 upsert by memory id | Done | `cd team_cloud && go test ./... && go vet ./... && go build -o /tmp/hermes-team-cloud-server ./cmd/team-cloud-server` |
| GTC-73 | Dashboard 记忆治理自动加载、备份管理、权限中心只读角色说明 | Done | `cd team_cloud/dashboard && npm test -- --run && npm run type-check && npm run build` |
| GTC-74 | 文档、release manual、minikube 手册同步 | Done | `teamDoc/`, `teamDoc/releaseManual/` |
| GTC-75 | 非破坏性镜像重建和 Kubernetes rolling update | Done | `hermes-team-cloud-go:gtc75-20260524171148`; `kubectl rollout status deployment/hermes-team-cloud-go -n hermes-team-cloud --timeout=180s`; PVC preserved |

## 执行顺序

1. 先补测试，锁定 CLI 配置/备份包、Team Cloud 熔断、团队记忆备份恢复幂等、Dashboard 交互预期。
2. 实现 CLI 本地个人记忆备份，不触碰云端个人记忆数据。
3. 实现 Team Cloud 团队记忆备份 API；旧个人备份 API 已退役，不保留兼容入口。
4. 重构 Dashboard 文案和页面：记忆治理进入即加载，备份策略更名备份管理，权限中心不再暴露关系写入表单。
5. 更新文档和验收手册。
6. 若 schema 仅追加兼容字段或复用既有表，则执行非破坏性滚动更新；只有不可避免时才清空 PVC。
