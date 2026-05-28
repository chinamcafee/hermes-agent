# 2026-05-24 Team Memory Backup and CLI Polish Log

## 输入需求

- 云端 Team Cloud 只管理团队记忆，个人记忆不再由云端管理。
- CLI 增加 `/memory-backup`，支持 MinIO 配置、周期、备份、恢复。
- Dashboard 记忆治理进入即加载；备份页改为团队记忆备份管理；权限中心去掉可编辑权限关系表单。
- CLI 团队模式需要常驻状态栏标识，并具备 Team Cloud API 熔断和恢复控制。

## 当前执行计划

1. 补充 GTC-69 到 GTC-75 任务拆解。
2. 按 TDD 为 CLI 和 Go/Dashboard 补失败测试。
3. 实现 CLI 本地个人记忆备份和 Team Cloud 熔断。
4. 实现 Go 团队记忆备份 API、恢复幂等 upsert、Dashboard 备份管理。
5. 更新 release manual 和 minikube 手册。
6. 通过验证后执行非破坏性镜像重建和 Kubernetes rolling update。

## 风险记录

- 旧文档大量写死 `Casdoor + SpiceDB + PostgreSQL + MinIO` 为必备组合，本轮需要统一改成 MinIO 可选。
- Go 服务旧的个人备份 API 已存在，为降低破坏面，先保留兼容但从 GA 主路径、TeamMemoryProvider 和 Dashboard 中移除。
- CLI 定时备份依赖 Hermes cron；自动执行要求 gateway/scheduler 运行，这一点需要在手册中明确。

## 完成记录

- `TeamMemoryProvider` 只召回 `team_shared`，请求中固定 `include_personal=false`；移除云端 personal remember 和 personal backup 工具暴露。
- Hermes CLI 新增 `/memory-backup` 和 `hermes memory-backup`，负责本地 profile 个人记忆的 MinIO/S3-compatible 配置、周期、手动备份、历史和恢复。
- `/team` 增加 API 熔断状态和 `breaker status|open|close|auto` 控制，CLI 状态栏能显示 Team / Team API paused。
- Go 服务新增团队记忆备份策略、历史、立即备份和恢复 API；恢复按 memory id upsert，重复恢复不会产生同 id 重复记录。
- Dashboard “记忆治理”进入即刷新；“备份策略”改为“备份管理”，只管理团队记忆备份；“权限中心”改为只读角色矩阵。
- 文档同步更新 `README`、架构、数据管理、GA 需求、Go 服务设计、CLI 边界、Dashboard V2、release manual 和 minikube 手册。

## 验证记录

- `venv/bin/python -m pytest tests/hermes_cli/test_memory_backup_cli.py tests/hermes_cli/test_team_cloud_cli.py tests/team_cloud/test_team_memory_provider.py tests/team_cloud/test_team_memory_provider_tools.py tests/run_agent/test_memory_provider_init.py -q`：26 passed。
- `venv/bin/python -m py_compile hermes_cli/memory_backup.py hermes_cli/team_cloud.py team_cloud/memory/provider.py cli.py agent/agent_init.py`：exit 0。
- `cd team_cloud && go test ./...`：exit 0。
- `cd team_cloud && go vet ./...`：exit 0。
- `cd team_cloud && go build ./cmd/team-cloud-server`：exit 0。
- `cd team_cloud/dashboard && npm test -- --run`：11 passed。
- `cd team_cloud/dashboard && npm run type-check`：exit 0。
- `cd team_cloud/dashboard && npm run build`：exit 0。

## Kubernetes 发布记录

- 发布方式：非破坏性 rolling update，保留 `data-postgres-0`、`data-redis-0`、`data-minio-0` PVC 和既有初始化数据。
- 当前镜像：`hermes-team-cloud-go:gtc75-20260524171148`。
- 部署验证：`kubectl rollout status deployment/hermes-team-cloud-go -n hermes-team-cloud --timeout=180s` 返回 `deployment "hermes-team-cloud-go" successfully rolled out`。
- 运行状态：`deployment/hermes-team-cloud-go` 为 `2/2` ready；`postgres-0`、`redis-0`、`spicedb`、`minio-0` 均 Running。
- 入口：`screen` 会话 `hermes-team-cloud-tunnel` 维持 `127.0.0.1:8780 -> svc/hermes-team-cloud-go:8780`，Dashboard 访问 `http://127.0.0.1:8780/dashboard/`。
- Bootstrap smoke：`GET /v1/bootstrap/status` 返回 `status=ready`、`initialized=true`、`super_admin_count=1`、`backup_object_store=true`、`minio_configured=false`，确认对象存储不再是初始化必备项。
- 镜像清理：minikube 中仅保留当前项目服务端镜像 `docker.io/library/hermes-team-cloud-go:gtc75-20260524171148`。
