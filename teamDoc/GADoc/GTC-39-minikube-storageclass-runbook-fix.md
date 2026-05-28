# GTC-39 minikube StorageClass Runbook 修复

日期：2026-05-23

## 范围

修复 Team Cloud Go + Dashboard minikube 手册中 PostgreSQL/MinIO 持久卷部署的缺失前置条件，避免本地 Kubernetes 初次部署在 PVC 绑定阶段卡住。

## 问题

在未启用 minikube 默认动态存储时，PostgreSQL `StatefulSet` 创建的 `data-postgres-0` PVC 无法绑定 PV，`postgres-0` Pod 事件显示：

```text
pod has unbound immediate PersistentVolumeClaims
```

PVC 事件进一步显示：

```text
no persistent volumes available for this claim and no storage class is set
```

## 决策

- minikube 手册必须在部署有状态中间件前启用 `storage-provisioner` 和 `default-storageclass`。
- PostgreSQL 和 MinIO 的示例 PVC 模板显式使用 `storageClassName: standard`，降低对隐式默认类的依赖。
- 排障章节保留对已创建 Pending PVC 的恢复路径，说明启用默认类后通常会自动绑定。

## 影响文件

- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `teamDoc/GALog/2026-05-23-minikube-storageclass-fix.md`
- `teamDoc/GAStep/progress-tracker.md`

## 验证

- `kubectl get storageclass`：确认 `standard (default)` 存在。
- `kubectl describe pvc data-postgres-0 -n hermes-team-cloud`：确认 `StorageClass: standard`、`Status: Bound`、`ProvisioningSucceeded`。
- `kubectl get pods -n hermes-team-cloud -o wide`：确认 `postgres-0` 为 `1/1 Running`。
- `ruby -e 'require "yaml"; YAML.load_stream(File.read("team_cloud/deploy/kubernetes/team-cloud-go.yaml")); puts "ok"'`：确认服务端 Kubernetes manifest YAML 可解析。
- `git diff --check -- teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md teamDoc/GALog/2026-05-23-minikube-storageclass-fix.md teamDoc/GADoc/GTC-39-minikube-storageclass-runbook-fix.md teamDoc/GAStep/progress-tracker.md`：确认文档 diff 无尾随空白。

