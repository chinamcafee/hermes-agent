# minikube 镜像构建路径修复日志

日期：2026-05-23

## 背景

继续验证 Team Cloud Go + Dashboard minikube 手册时，`minikube image build --all -t hermes-team-cloud-go:minikube .` 在当前 profile 上触发多节点构建路径，其中一个 worker 的 Docker build 在 `go mod download` 阶段解析 `proxy.golang.org` 超时。

## 根因

- 当前 minikube profile 是 3 节点 profile，但 `kubectl get nodes` 只显示一个 Ready control-plane 节点。
- `--all` 会尝试对 profile 中多个 minikube 节点构建镜像；stopped worker 或 worker 内 DNS 异常会影响本地演练。
- 本地单 Ready 节点演练并不需要 `--all`。

## 修复

- 手册默认镜像构建命令改为 `minikube image build -t hermes-team-cloud-go:minikube .`。
- `--all` 改为多 Ready 节点场景的可选命令。
- 手册新增 `--all` 失败时的判断：先看 `kubectl get nodes`，单 Ready 节点用默认命令，多 Ready 节点先恢复 worker 再重试。

## 现场验证

- `minikube image ls | rg 'hermes-team-cloud-go|minikube'` 显示 `docker.io/library/hermes-team-cloud-go:minikube` 已存在。
- `minikube image build -t hermes-team-cloud-go:minikube .` 通过，输出镜像 digest `sha256:06c4a983b306730d25e4b6cab308c007f55bb17c95a7d3d7bae4743d488e2dad`。

