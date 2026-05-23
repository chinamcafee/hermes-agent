# Team Cloud Go + Dashboard minikube 本地 Kubernetes 部署手册

版本：Team Cloud Go Dashboard GA
日期：2026-05-23

## 适用范围

本文用于在本机 minikube 中部署：

- `team_cloud_go` Go 服务端和内置 `/dashboard/` 管理台。
- PostgreSQL + pgvector。
- SpiceDB/Authzed compatible HTTP API。
- MinIO 对象存储。
- 本地 Hermes dashboard/CLI 编译，并连接 minikube 中的 Team Cloud Go 服务。

Python `team_cloud/` 不参与本手册部署路径。

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

构建镜像时使用 minikube Docker daemon：

```bash
eval "$(minikube docker-env)"
```

## 2. 创建 Secret

```bash
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_SERVICE_TOKEN='dev-team-cloud-token' \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID='minioadmin' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY='minioadmin123' \
  --from-literal=TEAM_CLOUD_BACKUP_ENCRYPTION_KEY='local-minikube-backup-key-change-me'
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
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 8Gi
YAML

kubectl rollout status statefulset/postgres
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

## 5. 部署 MinIO

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
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 8Gi
YAML

kubectl rollout status statefulset/minio
kubectl run minio-client --rm -i --restart=Never --image=quay.io/minio/mc:RELEASE.2025-08-13T08-35-41Z -- \
  sh -c 'mc alias set local http://minio:9000 minioadmin minioadmin123 && mc mb -p local/hermes-personal-backups'
```

## 6. 构建并部署 Team Cloud Go + Dashboard

```bash
cd /Users/changzechuan/AIProjects/AgentProjects/HermesProjects/hermes-agent/team_cloud_go
npm --prefix dashboard ci
npm --prefix dashboard test -- --run
npm --prefix dashboard run build
go test ./...
docker build -t hermes-team-cloud-go:minikube .
```

如果没有使用 `eval "$(minikube docker-env)"`，改用：

```bash
minikube image load hermes-team-cloud-go:minikube
```

应用 Go 服务 manifest：

```bash
kubectl apply -f deploy/kubernetes/team-cloud-go.yaml
kubectl create secret generic hermes-team-cloud-go-secrets \
  --from-literal=TEAM_CLOUD_SERVICE_TOKEN='dev-team-cloud-token' \
  --from-literal=TEAM_CLOUD_DATABASE_URL='postgres://hermes:hermespass@postgres:5432/hermes_team_cloud?sslmode=disable' \
  --from-literal=TEAM_CLOUD_AUTHZ_TOKEN='spicedb-dev-key' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_ACCESS_KEY_ID='minioadmin' \
  --from-literal=TEAM_CLOUD_BACKUP_S3_SECRET_ACCESS_KEY='minioadmin123' \
  --from-literal=TEAM_CLOUD_BACKUP_ENCRYPTION_KEY='local-minikube-backup-key-change-me' \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl set image deployment/hermes-team-cloud-go team-cloud-go=hermes-team-cloud-go:minikube
kubectl set env deployment/hermes-team-cloud-go \
  TEAM_CLOUD_AUTHZ_ENDPOINT=http://spicedb:8443 \
  TEAM_CLOUD_BACKUP_S3_ENDPOINT=http://minio:9000 \
  TEAM_CLOUD_BACKUP_S3_BUCKET=hermes-personal-backups \
  TEAM_CLOUD_DASHBOARD_ENABLED=true \
  TEAM_CLOUD_DASHBOARD_DIR=/usr/share/team-cloud-go/dashboard
kubectl rollout status deployment/hermes-team-cloud-go
```

重新 apply Secret 是为了覆盖示例 manifest 中的占位值，确保 minikube 使用本手册的本地 PostgreSQL、SpiceDB 和 MinIO 凭据。

## 7. 打开 Dashboard 并初始化

```bash
kubectl port-forward svc/hermes-team-cloud-go 8780:8780
```

浏览器打开：

```text
http://localhost:8780/dashboard/
```

初始化：

1. API 地址留空，表示使用同源 `/api` 和 `/v1`。
2. Service token 填 `dev-team-cloud-token`。
3. 点击“检查服务”，确认 `backend/authz/dashboard` ready。
4. 在“初始化”页创建组织 `hermes-labs` 和超级管理员 `owner`。
5. 在“组织”页创建团队 `platform`，邀请成员。
6. 在“权限”页为成员写入团队关系并执行 permission check。
7. 在“备份”页保存个人记忆备份策略并运行一次立即备份。

API 验证：

```bash
curl -sS http://localhost:8780/v1/bootstrap/status | python -m json.tool
curl -sS -H 'Authorization: Bearer dev-team-cloud-token' http://localhost:8780/api/organizations | python -m json.tool
```

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
HERMES_TEAM_CLOUD_URL=http://localhost:8780 \
HERMES_TEAM_CLOUD_SERVICE_TOKEN=dev-team-cloud-token \
hermes
```

Gateway 团队身份解析可使用环境变量：

```bash
export HERMES_GATEWAY_TEAM_IDENTITY_ENABLED=true
export HERMES_TEAM_CLOUD_URL=http://localhost:8780
export HERMES_TEAM_CLOUD_SERVICE_TOKEN=dev-team-cloud-token
hermes gateway
```

也可以写入 `~/.hermes/config.yaml`：

```yaml
gateway:
  team_identity:
    enabled: true
    team_cloud_url: http://localhost:8780
    service_token: dev-team-cloud-token
```

本地 Hermes dashboard/CLI 的职责是连接远程 Team Cloud、运行本地 Agent、管理本地个人环境和 gateway 配置。团队组织、成员、权限、记忆审核、备份和审计管理使用 `http://localhost:8780/dashboard/`。

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
- `backup_object_store=false`：MinIO bucket、access key 或 endpoint 不一致。
- `dashboard=false`：镜像没有包含 `/usr/share/team-cloud-go/dashboard` 或 env 被关闭。

清理环境：

```bash
kubectl delete namespace hermes-team-cloud
minikube stop
```
