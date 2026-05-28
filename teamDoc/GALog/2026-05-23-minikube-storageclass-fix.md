# minikube StorageClass 部署修复日志

日期：2026-05-23

## 背景

本地 minikube 部署 PostgreSQL `StatefulSet` 时，`postgres-0` Pod 停在 `Pending`，事件显示 `pod has unbound immediate PersistentVolumeClaims`。进一步查看 PVC 事件，根因为集群没有默认 `StorageClass`，动态卷无法为 `data-postgres-0` 创建 PV。

## 根因

- 原手册直接创建 PostgreSQL 和 MinIO 的 PVC，但没有要求先启用 minikube `storage-provisioner` 和 `default-storageclass` addon。
- PostgreSQL/MinIO 的 `volumeClaimTemplates` 未显式声明 `storageClassName`，依赖集群默认类；当默认类缺失时，PVC 无法绑定。

## 修复

- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md` 前置条件新增：
  - `minikube addons enable storage-provisioner`
  - `minikube addons enable default-storageclass`
  - `kubectl get storageclass` 验证默认 `standard` 类。
- PostgreSQL 和 MinIO 的 PVC 模板新增 `storageClassName: standard`，与 minikube 默认本地存储类对齐。
- 排障章节新增 PVC Pending 的诊断和恢复命令。

## 现场验证

- `kubectl get storageclass` 已显示 `standard (default)`，provisioner 为 `k8s.io/minikube-hostpath`。
- `kubectl describe pvc data-postgres-0 -n hermes-team-cloud` 显示 PVC 已绑定到 `standard`，并出现 `ProvisioningSucceeded`。
- `kubectl get pods -n hermes-team-cloud -o wide` 显示 `postgres-0` 已进入 `Running`。

