# Kubernetes distroless nonroot UID 修复日志

日期：2026-05-23

## 背景

继续验证 Team Cloud Go + Dashboard minikube 部署时，Deployment 切换到本地镜像后新 Pod 进入 `CreateContainerConfigError`。

## 根因

`gcr.io/distroless/static-debian12:nonroot` 镜像使用 `nonroot` 用户名。Kubernetes 在 `runAsNonRoot: true` 且未设置数字 UID 时，无法确认镜像用户是否非 root，因此拒绝创建容器：

```text
container has runAsNonRoot and image has non-numeric user (nonroot), cannot verify user is non-root
```

## 修复

- `team_cloud/deploy/kubernetes/team-cloud-go.yaml` 的 Pod `securityContext` 新增：
  - `runAsUser: 65532`
  - `runAsGroup: 65532`
- `team_cloud/internal/deploy/deploy_test.go` 新增 manifest 断言，防止该字段回归。
- minikube 手册排障章节加入 `CreateContainerConfigError` 的检查和 patch 命令。

## TDD 记录

- 红灯：`go test ./internal/deploy -count=1` 失败，提示 Kubernetes manifest missing `runAsUser: 65532`。
- 绿灯：manifest 加入 UID/GID 后，`go test ./internal/deploy -count=1` 通过。

## 现场验证

- `kubectl patch deployment hermes-team-cloud-go ... runAsUser/runAsGroup ...` 后 rollout 成功。
- `kubectl get deployment hermes-team-cloud-go -n hermes-team-cloud -o wide` 显示 `READY 2/2`，镜像为 `hermes-team-cloud-go:minikube`。
- `curl http://127.0.0.1:18780/readyz` 返回 `status: ready`，backend/authz/backup/config 均为 `true`。
- `curl http://127.0.0.1:18780/v1/bootstrap/status` 返回 `dashboard: true`、`service_token_configured: true`。

