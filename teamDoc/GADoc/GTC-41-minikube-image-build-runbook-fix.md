# GTC-41 minikube 镜像构建 Runbook 修复

日期：2026-05-23

## 范围

修复 Team Cloud Go + Dashboard minikube 手册中镜像构建路径，避免多节点 profile 下 stopped worker 或 worker DNS 问题影响单节点本地演练。

## 问题

`minikube image build --all -t hermes-team-cloud-go:minikube .` 在当前 profile 上尝试多节点构建，其中一个节点的 Docker build 在 `go mod download` 阶段出现：

```text
lookup proxy.golang.org on 192.168.65.254:53: i/o timeout
```

## 决策

- 默认命令使用 `minikube image build -t hermes-team-cloud-go:minikube .`。
- 只有 `kubectl get nodes` 显示多个 Ready 节点，且 Pod 可能调度到任意 worker 时，才使用 `--all`。
- 如果 `--all` 失败，先恢复 worker 或改用单 Ready 节点路径，不再把 `--all` 作为默认要求。

## 影响文件

- `teamDoc/releaseManual/team-cloud-go-minikube-dashboard-manual.md`
- `teamDoc/GALog/2026-05-23-minikube-image-build-fix.md`
- `teamDoc/GAStep/progress-tracker.md`

## 验证

- `minikube image build -t hermes-team-cloud-go:minikube .`：通过。
- `minikube image ls | rg 'hermes-team-cloud-go|minikube'`：确认镜像存在于 minikube image store。

