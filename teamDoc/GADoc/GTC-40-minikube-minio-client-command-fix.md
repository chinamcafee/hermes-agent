# GTC-40 minikube MinIO Client 命令修复

日期：2026-05-23

## 范围

修复 Team Cloud Go + Dashboard minikube 手册中 MinIO bucket 初始化命令，确保本地 Kubernetes 演练可以创建 `hermes-personal-backups` bucket。

## 问题

`quay.io/minio/mc` 镜像默认以 `mc` 为 entrypoint。未使用 `kubectl run --command` 时，`sh -c` 会被传给 `mc`，导致命令失败。

## 决策

手册统一使用：

```bash
kubectl run minio-client --rm -i --restart=Never --image=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z --command -- \
  sh -c 'mc alias set local http://minio:9000 minioadmin minioadmin123 && mc mb -p local/hermes-personal-backups'
```

## 影响文件

- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `teamDoc/GALog/2026-05-23-minikube-minio-client-fix.md`
- `teamDoc/GAStep/progress-tracker.md`

## 验证

- `kubectl run minio-client -n hermes-team-cloud --rm -i --restart=Never --image=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z --command -- sh -c 'mc alias set local http://minio:9000 minioadmin minioadmin123 && mc mb -p local/hermes-personal-backups'`：通过。
- `kubectl get pods,svc,pvc -n hermes-team-cloud`：PostgreSQL、SpiceDB、MinIO 均为 Running，PostgreSQL/MinIO PVC 均为 Bound。

