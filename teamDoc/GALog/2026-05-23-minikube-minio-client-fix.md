# minikube MinIO Client 初始化命令修复日志

日期：2026-05-23

## 背景

继续验证 Team Cloud Go + Dashboard minikube 手册时，MinIO 服务和 PVC 均正常，但 bucket 初始化命令失败。

## 根因

`quay.io/minio/mc` 镜像默认入口是 `mc`。原手册命令使用：

```bash
kubectl run ... -- \
  sh -c 'mc alias set ...'
```

这会把 `sh` 当成 `mc` 子命令执行，因此报错：

```text
mc: <ERROR> `sh` is not a recognized command.
```

## 修复

手册中的 bucket 初始化命令改为：

```bash
kubectl run minio-client --rm -i --restart=Never --image=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z --command -- \
  sh -c 'mc alias set local http://minio:9000 minioadmin minioadmin123 && mc mb -p local/hermes-personal-backups'
```

## 现场验证

- `kubectl rollout status statefulset/minio -n hermes-team-cloud --timeout=240s` 已通过。
- `kubectl describe pvc data-minio-0 -n hermes-team-cloud` 显示 `StorageClass: standard`、`Status: Bound`。
- 修正后的 `kubectl run minio-client ... --command -- sh -c ...` 成功输出 `Added local successfully` 和 `Bucket created successfully local/hermes-personal-backups`。

