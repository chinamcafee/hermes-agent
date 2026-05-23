# 05. Phase 4-5：Beta 验证与 GA 发布

## Phase 4：Beta 验证

### 1. 部署硬化

1. Docker Compose 加 healthcheck。
2. Compose volume 和 backup mount 固化。
3. Helm chart 支持 ingress、TLS、secret、persistence。
4. Offline bundle 打包镜像、chart、checksum。
5. 安装脚本做环境检查。

### 2. 观测

1. Team API metrics。
2. SpiceDB check latency 和 deny rate。
3. PostgreSQL/pgvector query latency。
4. MinIO upload/download latency。
5. Worker lag。
6. Audit/security dashboards。
7. request_id/run_id 全链路日志串联。

### 3. 压测

1. 并发 chat runs。
2. 并发 memory prefetch。
3. 批量 SpiceDB check。
4. 大量 memory embedding import。
5. 定时 personal backup。
6. 组织导出。
7. Gateway group session。

### 4. 安全测试

1. 伪造 Casdoor token。
2. 错误 audience/issuer。
3. disabled member access。
4. cross-org memory query。
5. prompt injection 诱导读取 personal memory。
6. tool bypass。
7. break-glass abuse。
8. MinIO signed URL 越权。

### 5. 备份恢复演练

1. PostgreSQL PITR。
2. SpiceDB relationship snapshot + outbox replay。
3. MinIO bucket restore。
4. Casdoor 配置恢复。
5. 单成员 personal backup restore。
6. 组织导出回灌。

### 6. 试点

1. 选择 3 个团队。
2. 导入成员和初始项目。
3. 配置 Gateway 平台。
4. 连续运行 2 周。
5. 每周汇总 usage、latency、errors、security events。
6. 输出 Beta exit report。

## Phase 5：GA 发布

1. 修复 Beta blocker。
2. 完成最终安全复测。
3. 生成 SBOM。
4. 完成 license report，特别说明 MinIO AGPL-3.0。
5. 完成安装指南。
6. 完成管理员手册。
7. 完成用户手册。
8. 完成 API 文档。
9. 完成 backup/restore/outage/upgrade/rollback Runbook。
10. 完成 release notes。
11. 完成 support playbook。
12. 执行 final regression。
13. 新环境执行 deployment smoke。
14. 完成 GA sign-off。
15. 建立 Post-GA backlog。

## GA 出口标准

- P0/P1 安全缺陷为 0。
- 权限矩阵正反用例 100% 通过。
- 备份恢复演练 100% 通过。
- 3 个试点团队连续 2 周无阻塞故障。
- 新环境可按文档部署成功。
- 所有 Runbook 有演练证据。

