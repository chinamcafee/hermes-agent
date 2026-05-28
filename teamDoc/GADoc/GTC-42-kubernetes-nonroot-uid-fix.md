# GTC-42 Kubernetes distroless nonroot UID 修复

日期：2026-05-23

## 范围

修复 Team Cloud Go Kubernetes manifest 中 distroless nonroot 镜像与 `runAsNonRoot` 的兼容问题，并补齐部署测试和 minikube 排障文档。

## 问题

本地 minikube 部署时，新 Pod 进入 `CreateContainerConfigError`，事件显示：

```text
container has runAsNonRoot and image has non-numeric user (nonroot), cannot verify user is non-root
```

## 决策

distroless `nonroot` 对应 UID/GID 为 `65532`。Deployment Pod `securityContext` 显式声明：

```yaml
runAsNonRoot: true
runAsUser: 65532
runAsGroup: 65532
```

## 影响文件

- `team_cloud/deploy/kubernetes/team-cloud-go.yaml`
- `team_cloud/internal/deploy/deploy_test.go`
- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `teamDoc/GALog/2026-05-23-kubernetes-nonroot-uid-fix.md`
- `teamDoc/GAStep/progress-tracker.md`

## 验证

- `go test ./internal/deploy -count=1`：红灯阶段缺少 `runAsUser: 65532`，修复后通过。
- `kubectl rollout status deployment/hermes-team-cloud-go -n hermes-team-cloud --timeout=240s`：通过。
- `kubectl get pods,svc,pvc -n hermes-team-cloud`：Team Cloud Go、PostgreSQL、SpiceDB、MinIO 均 Running。
- `curl -sS http://127.0.0.1:18780/readyz | python -m json.tool`：返回 ready。
- `curl -sS http://127.0.0.1:18780/v1/bootstrap/status | python -m json.tool`：返回 backend/authz/backup/dashboard ready。
- `curl -sS -D - http://127.0.0.1:18780/dashboard/`：返回 HTTP 200 和 Dashboard HTML。

