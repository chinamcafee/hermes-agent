# 2026-05-24 Team Cloud Go 目录收口与文档脚本清理

## 背景

用户确认旧 Team Cloud 服务端已删除，原 Go 服务目录已重命名为当前 `team_cloud/`，并要求所有源码、脚本和权威文档以 Go 服务端为准。

## 本次处理

- 将 `scripts/team-cloud-smoke.sh` 改为当前 Go 服务端、Dashboard 和 schema static smoke，不再寻找 `deploy/team-cloud/compose.yaml`。
- 将 `scripts/team-cloud-secrets.sh` 改为生成 `team_cloud/.local/secrets/team_cloud.env` 本地 Go 服务端 env 示例，不再写入旧 deploy secrets 目录。
- 将 `scripts/team-cloud-offline-bundle.sh` 改为复制 `team_cloud/` 当前 Dockerfile、Kubernetes manifest、README 和 release manual，并生成 `SHA256SUMS`。
- 更新 `teamDoc/README.md`、`03-target-architecture.md`、`10-implementation-backlog.md`、`12-ga-product-requirements.md`、`17-team-cloud-go-service-design.md`、P2/P5 GADoc、GAStep 和 release manual，明确当前 Team Cloud 服务端只有 `team_cloud/` Go 实现。
- 更新 Desktop `teamDoc` 中的旧 Go 服务目录路径为 `team_cloud/dashboard`，保持 Desktop 不直连 Team Cloud 的边界。
- 将 `progress-tracker.md` 的 GTC-86 标记为 Done，并写入 Desktop 主会话验证命令。

## 验证计划

- Hermes Agent：Python CLI/provider/soul/cloud-backup 测试、Go `go test/vet/build`、Dashboard test/typecheck/build、脚本 `bash -n` 和 `git diff --check`。
- Hermes Desktop：Bridge/Soul/Cloud Backup targeted Vitest、typecheck 和 `git diff --check`。
