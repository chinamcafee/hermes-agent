# Team Cloud + Dashboard minikube 本地 Kubernetes 部署手册

版本：Team Cloud Dashboard GA
日期：2026-05-23

## 适用范围

本文用于在本机 minikube 中部署：

- `team_cloud` Go 服务端和内置 `/dashboard/` 管理台。
- PostgreSQL + pgvector。
- SpiceDB/Authzed compatible HTTP API。
- 可选 MinIO 对象存储，用于团队记忆备份、团队父人格备份和 CLI 本地 memory/soul 备份演练。
- 本地 Hermes dashboard/CLI 编译，并连接 minikube 中的 Team Cloud 服务。

本手册只部署 `team_cloud/` Go 服务端和内置 Dashboard；旧 Python 服务端已经删除。

## 1. 前置条件

```bash
minikube version
kubectl version --client
docker version
node -v
npm -v
go version
python --version
```

建议资源：

```bash
minikube start --driver=docker --cpus=6 --memory=12288 --disk-size=40g
kubectl create namespace hermes-team-cloud
kubectl config set-context --current --namespace=hermes-team-cloud
```

确认节点状态：

```bash
kubectl get nodes
```

如果是 multi-node 集群，所有需要承载 Pod 的节点都应为 `Ready`。如果 `minikube status` 显示 worker `kubelet: Stopped`，先启动节点：

```bash
minikube node start minikube-m02
minikube node start minikube-m03
kubectl get nodes
```

启用 minikube 本地动态存储。PostgreSQL 必须使用 `StatefulSet` + PVC；如果要演练 MinIO，MinIO 也会使用 PVC。如果集群没有默认 `StorageClass`，Pod 会停在 `Pending`，并出现 `pod has unbound immediate PersistentVolumeClaims`：

```bash
minikube addons enable storage-provisioner
minikube addons enable default-storageclass
kubectl get storageclass
```

期望看到类似：

```text
NAME                 PROVISIONER                RECLAIMPOLICY   VOLUMEBINDINGMODE
standard (default)   k8s.io/minikube-hostpath   Delete          Immediate
```

如果 `standard` 存在但没有 `(default)`，为本地演练补默认标记：

```bash
kubectl patch storageclass standard \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
kubectl get storageclass
```

镜像构建默认使用 minikube image 子命令。本手册不要求执行 `eval "$(minikube docker-env)"`；该命令只适用于单节点 minikube，多节点会报 `ENV_MULTINODE_CONFLICT`。

单节点集群可选使用：

```bash
eval "$(minikube docker-env)"
```

## 2. 创建 Secret

```bash
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_REDIS_PASSWORD='redispass' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key'
```

如果本次要演练 Team Cloud 团队记忆对象备份，再追加 S3/MinIO 凭据：

```bash
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_REDIS_PASSWORD='redispass' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID='minioadmin' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY='minioadmin123' \
  --from-literal=TEAM_CLOUD_BACKUP_ENCRYPTION_KEY='local-minikube-backup-key-change-me' \
  --dry-run=client -o yaml | kubectl apply -f -
```

## 3. 部署 PostgreSQL + pgvector

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
  selector:
    app: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: pgvector/pgvector:0.8.2-pg18-trixie
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_DB
              value: hermes_team_cloud
            - name: POSTGRES_USER
              value: hermes
            - name: POSTGRES_PASSWORD
              value: hermespass
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        storageClassName: standard
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 8Gi
YAML

kubectl rollout status statefulset/postgres
until kubectl exec statefulset/postgres -- psql -U hermes -d hermes_team_cloud -c 'select 1;' >/dev/null 2>&1; do
  sleep 2
done
kubectl exec statefulset/postgres -- psql -U hermes -d hermes_team_cloud -c 'create extension if not exists vector;'
```

## 4. 部署 SpiceDB

本地演练使用内存 datastore。生产部署必须使用持久化 datastore 并加载正式 schema。

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: spicedb
spec:
  ports:
    - name: http
      port: 8443
      targetPort: 8443
  selector:
    app: spicedb
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: spicedb
spec:
  replicas: 1
  selector:
    matchLabels:
      app: spicedb
  template:
    metadata:
      labels:
        app: spicedb
    spec:
      containers:
        - name: spicedb
          image: ghcr.io/authzed/spicedb:v1.53.0-debug
          args:
            - serve
            - --grpc-preshared-key=spicedb-dev-key
            - --http-enabled=true
            - --http-addr=:8443
            - --datastore-engine=memory
          ports:
            - containerPort: 8443
YAML

kubectl rollout status deployment/spicedb
```

## 5. 可选部署 MinIO

Team Cloud Go 初始化不要求 MinIO。只有需要验收“备份管理”的团队记忆或团队父人格对象上传，或需要给本机 Hermes CLI `/cloud-backup memory|soul` 提供本地对象存储时，才部署本节。

```bash
cat <<'YAML' | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: minio
spec:
  ports:
    - name: api
      port: 9000
      targetPort: 9000
    - name: console
      port: 9001
      targetPort: 9001
  selector:
    app: minio
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: minio
spec:
  serviceName: minio
  replicas: 1
  selector:
    matchLabels:
      app: minio
  template:
    metadata:
      labels:
        app: minio
    spec:
      containers:
        - name: minio
          image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
          args: ["server", "/data", "--console-address", ":9001"]
          env:
            - name: MINIO_ROOT_USER
              value: minioadmin
            - name: MINIO_ROOT_PASSWORD
              value: minioadmin123
          ports:
            - containerPort: 9000
            - containerPort: 9001
          volumeMounts:
            - name: data
              mountPath: /data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        storageClassName: standard
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 8Gi
YAML

kubectl rollout status statefulset/minio
kubectl run minio-client --rm -i --restart=Never --image=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z --command -- \
  sh -c 'until mc alias set local http://minio:9000 minioadmin minioadmin123; do sleep 2; done && mc mb -p local/hermes-team-memory-backups || true && mc mb -p local/hermes-team-soul-backups || true'
```

## 6. 构建并部署 Team Cloud Go + Dashboard

```bash
cd /Users/changzechuan/AIProjects/AgentProjects/HermesProjects/hermes-agent/team_cloud
npm --prefix dashboard ci
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
go test ./...
minikube image build -t hermes-team-cloud-go:minikube .
```

如果 `kubectl get nodes` 显示多个 Ready 节点，并且 Pod 可能调度到任意 worker，再把镜像构建到所有 minikube 节点：

```bash
minikube image build --all -t hermes-team-cloud-go:minikube .
```

如果 `--all` 因 stopped worker、worker DNS 或 `proxy.golang.org` 解析超时失败，先确认 `kubectl get nodes` 中实际 Ready 的节点数量。单 Ready 节点本地演练使用不带 `--all` 的 `minikube image build -t ...` 即可；多 Ready 节点则先恢复 worker 后重试。

如果你是单节点集群并且已经成功执行 `eval "$(minikube docker-env)"`，也可以改用：

```bash
docker build -t hermes-team-cloud-go:minikube .
```

如果你已经在本机 Docker daemon 构建了镜像，改用加载路径：

```bash
docker build -t hermes-team-cloud-go:minikube .
minikube image load hermes-team-cloud-go:minikube
```

应用 Go 服务 manifest：

```bash
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_REDIS_PASSWORD='redispass' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl set image deployment/hermes-team-cloud-go team-cloud-go=hermes-team-cloud-go:minikube
kubectl set env deployment/hermes-team-cloud-go \
  TEAM_CLOUD_REDIS_ADDR=redis:6379 \
  TEAM_CLOUD_REDIS_DB=0 \
  TEAM_CLOUD_SESSION_TTL_SECONDS=43200 \
  TEAM_CLOUD_AUTHZ_ENDPOINT=http://spicedb:8443 \
  TEAM_CLOUD_DASHBOARD_ENABLED=true \
  TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard
kubectl rollout status deployment/hermes-team-cloud-go
```

重新 apply Secret 是为了覆盖示例 manifest 中的占位值，确保 minikube 使用本手册的本地 PostgreSQL 和 SpiceDB 凭据。

如果已经部署了 MinIO 并要启用团队记忆对象备份，再追加：

```bash
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_REDIS_PASSWORD='redispass' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID='minioadmin' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY='minioadmin123' \
  --from-literal=TEAM_CLOUD_BACKUP_ENCRYPTION_KEY='local-minikube-backup-key-change-me' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl set env deployment/hermes-team-cloud-go \
  TEAM_CLOUD_BACKUP_OBJECT_MODE=s3 \
  TEAM_CLOUD_BACKUP_S3_ENDPOINT=http://minio:9000 \
  TEAM_CLOUD_BACKUP_S3_BUCKET=hermes-team-memory-backups
kubectl rollout status deployment/hermes-team-cloud-go
```

当前示例使用 `TEAM_CLOUD_BACKUP_S3_BUCKET=hermes-team-memory-backups` 作为团队级备份 bucket。团队记忆对象 key 使用 `org/<org_id>/team-memory/...`，团队父人格对象 key 使用 `org/<org_id>/team-soul/...`；也可以在生产环境为不同资源配置独立 bucket 和生命周期策略。

## 7. 打开 Dashboard 并初始化

```bash
kubectl port-forward svc/hermes-team-cloud-go 8780:8780
```

如果希望验收期间关闭当前终端也保持本地入口，可以用 macOS 自带 `screen` 持有转发：

```bash
screen -dmS hermes-team-cloud-tunnel bash -lc \
  'kubectl port-forward --address 127.0.0.1 -n hermes-team-cloud svc/hermes-team-cloud-go 8780:8780 >/tmp/hermes-team-cloud-screen-port-forward.log 2>&1'
screen -ls
```

停止该转发：

```bash
screen -S hermes-team-cloud-tunnel -X quit
```

浏览器打开：

```text
http://localhost:8780/dashboard/
```

初始化：

1. API 地址留空，使用同源 `/v1` 和 `/api`。
2. 初始化页只展示 PostgreSQL、Redis Session 和可选对象存储的健康状态；连接由 Kubernetes Secret / env 注入，不需要在页面填写。
3. 按 Step-by-Step 向导依次填写团队名称、超级管理员帐号和密码。
4. 最后一步确认信息并点击“完成初始化”。
5. 初始化完成后，使用 `owner` 和刚设置的密码登录管理台；登录成功后服务端签发 Redis 保存的 `hcs_...` session token。
6. 在“团队成员”页直接创建管理员和用户；超级管理员可以创建管理员和用户，管理员只能创建用户。成员页支持查询、角色筛选、编辑邮箱/显示名和停用普通成员，唯一超级管理员不可停用。
7. 在“权限中心”“记忆治理”“备份管理”“审计时间线”“本地连接”页面完成对应管理操作。
8. “记忆治理”页现在包含团队记忆库、待审队列、停用和彻底删除按钮。创建团队记忆、编辑团队记忆和审核待审记忆通过弹窗完成，不在 Tab 页面堆叠表单。自动抽取的团队记忆显示“自动抽取”标签并标记来源成员；管理员直接创建的团队记忆显示“管理员创建”标签并标记创建者。

API 验证：

```bash
curl -sS http://localhost:8780/v1/bootstrap/status | python -m json.tool
```

Token 说明：

- Team Cloud Go 不再使用部署级 Service token 完成 Dashboard 初始化。
- Dashboard 登录后得到的 `hcs_...` token 存在浏览器 sessionStorage；服务端只在 Redis 中保存 token 摘要和 principal。
- CLI/Gateway 后续应使用成员级 token、OIDC/JWT 或后续 PAT 机制连接 Team Cloud，不再把 bootstrap token 作为普通成员凭据。

## 8. 编译本地 Hermes dashboard/CLI

```bash
cd /Users/changzechuan/AIProjects/AgentProjects/HermesProjects/hermes-agent
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
pip install -e .

cd ui-tui
npm install
npm run build
cd ..
```

启动本地 Hermes dashboard：

```bash
hermes dashboard
```

启动本地 Hermes CLI：

```bash
hermes team connect http://localhost:8780
hermes team login --org hermes-labs --user alice --project default
hermes team status
hermes
```

说明：

- `hermes team connect` 只保存 Team Cloud 服务地址。
- `hermes team login` 使用 Team Cloud Go 成员帐号密码登录，普通 `user` 成员也可以登录 CLI；Dashboard 管理页登录仍只允许 `super_admin/admin`。
- 登录成功后，非敏感上下文写入当前 Hermes profile 的 `config.yaml`，session token 写入当前 profile 的 `.env` 中的 `HERMES_TEAM_CLOUD_SESSION_TOKEN`。
- `hermes team status` 应显示 `mode: team`、`remote: ready` 和当前 `member`。

Gateway 团队身份解析可使用环境变量：

```bash
export HERMES_GATEWAY_TEAM_IDENTITY_ENABLED=true
export HERMES_TEAM_CLOUD_URL=http://localhost:8780
hermes gateway
```

也可以写入 `~/.hermes/config.yaml`：

```yaml
gateway:
  team_identity:
    enabled: true
    team_cloud_url: http://localhost:8780
    auth_mode: member_token
```

本地 Hermes dashboard/CLI/Desktop 的职责是通过 Hermes Agent Runtime Bridge 连接远程 Team Cloud、运行本地 Agent、管理本地个人环境和 gateway 配置。团队组织、成员、权限、记忆审核、备份和审计管理使用 `http://localhost:8780/dashboard/`。Hermes Desktop 不直连 Team Cloud Go 业务 API；它应调用本机或远端 Hermes Agent Bridge。

## 9. 常用排障

查看组件：

```bash
kubectl get pods,svc,pvc
kubectl logs deployment/hermes-team-cloud-go
kubectl logs statefulset/postgres
kubectl logs deployment/spicedb
kubectl logs statefulset/minio
```

readiness 不通过：

```bash
kubectl port-forward svc/hermes-team-cloud-go 8780:8780
curl -sS http://localhost:8780/readyz | python -m json.tool
```

常见原因：

- `backend=false`：PostgreSQL Secret DSN、Pod DNS 或 pgvector extension 异常。
- `authz=false`：SpiceDB HTTP endpoint 或 token 不一致。
- `backup_object_store=false`：仅在启用 `TEAM_CLOUD_BACKUP_OBJECT_MODE=s3` 时表示 MinIO/S3 bucket、access key 或 endpoint 不一致；未启用对象存储时不阻塞初始化。
- `dashboard=false`：镜像没有包含 `/usr/share/team-cloud-go/dashboard` 或 env 被关闭。

Redis Pod 出现 `CrashLoopBackOff`，并且日志显示 `chown: .: Operation not permitted`：

```bash
kubectl logs statefulset/redis --previous
kubectl get statefulset redis -o yaml | rg -n "command:|redis-server|fsGroup"
```

确认 Team Cloud Go manifest 中 Redis 容器显式覆盖默认 entrypoint：

```yaml
command:
  - redis-server
args:
  - --appendonly
  - "yes"
```

这是为了绕过官方 Redis 镜像 entrypoint 对 minikube PVC 挂载目录执行 `chown .` 的路径；卷权限由 Pod `fsGroup: 999` 处理。

Team Cloud Go Pod 出现 `CreateContainerConfigError`，并且 `kubectl describe pod` 显示 `image has non-numeric user (nonroot), cannot verify user is non-root`：

```bash
kubectl get deployment hermes-team-cloud-go -o yaml | rg -n "runAsNonRoot|runAsUser|runAsGroup"
```

确认 Deployment manifest 包含：

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 65532
  runAsGroup: 65532
```

如果本地集群已经创建了旧 Deployment，可直接 patch：

```bash
kubectl patch deployment hermes-team-cloud-go --type merge \
  -p '{"spec":{"template":{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":65532,"runAsGroup":65532,"seccompProfile":{"type":"RuntimeDefault"}}}}}}'
kubectl rollout status deployment/hermes-team-cloud-go
```

PVC 一直 `Pending`，并且 `kubectl describe pod postgres-0` 显示 `pod has unbound immediate PersistentVolumeClaims`：

```bash
kubectl get storageclass
kubectl describe pvc data-postgres-0
minikube addons enable storage-provisioner
minikube addons enable default-storageclass
kubectl get pvc -w
```

如果 PVC 是在没有默认 `StorageClass` 时创建的，启用上述 addon 后通常会自动绑定到 `standard`。如果仍然 Pending，确认 PVC 模板中的 `storageClassName` 与 `kubectl get storageclass` 输出一致；本手册默认使用 minikube 的 `standard`。

清理环境：

```bash
kubectl delete namespace hermes-team-cloud
minikube stop
```
