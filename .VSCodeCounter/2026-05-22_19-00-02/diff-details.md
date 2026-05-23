# Diff Details

Date : 2026-05-22 19:00:02

Directory /Users/changzechuan/AIProjects/AgentProjects/HermesProjects/hermes-agent

Total : 181 files,  14867 codes, 67 comments, 2906 blanks, all 17840 lines

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details

## Files
| filename | language | code | comment | blank | total |
| :--- | :--- | ---: | ---: | ---: | ---: |
| [agent/agent\_init.py](/agent/agent_init.py) | Python | 4 | 0 | 0 | 4 |
| [deploy/team-cloud/compose.yaml](/deploy/team-cloud/compose.yaml) | YAML | 371 | 0 | 19 | 390 |
| [deploy/team-cloud/init/postgres-init.sh](/deploy/team-cloud/init/postgres-init.sh) | Shell Script | 46 | 1 | 10 | 57 |
| [deploy/team-cloud/team-cloud.Dockerfile](/deploy/team-cloud/team-cloud.Dockerfile) | Docker | 10 | 0 | 7 | 17 |
| [deploy/team-cloud/web-shell/index.html](/deploy/team-cloud/web-shell/index.html) | HTML | 1,191 | 0 | 137 | 1,328 |
| [deploy/team-cloud/web-shell/nginx.conf](/deploy/team-cloud/web-shell/nginx.conf) | Properties | 9 | 0 | 3 | 12 |
| [gateway/platforms/api\_server.py](/gateway/platforms/api_server.py) | Python | 102 | 6 | 9 | 117 |
| [gateway/run.py](/gateway/run.py) | Python | 85 | 0 | 6 | 91 |
| [gateway/session.py](/gateway/session.py) | Python | 22 | 0 | 2 | 24 |
| [gateway/team\_identity.py](/gateway/team_identity.py) | Python | 206 | 1 | 39 | 246 |
| [pyproject.toml](/pyproject.toml) | TOML | 1 | 0 | 0 | 1 |
| [run\_agent.py](/run_agent.py) | Python | 2 | 0 | 0 | 2 |
| [scripts/team-cloud-foundation-smoke.sh](/scripts/team-cloud-foundation-smoke.sh) | Shell Script | 52 | 1 | 4 | 57 |
| [scripts/team-cloud-isolation-smoke.sh](/scripts/team-cloud-isolation-smoke.sh) | Shell Script | 19 | 1 | 4 | 24 |
| [scripts/team-cloud-secrets.sh](/scripts/team-cloud-secrets.sh) | Shell Script | 35 | 1 | 8 | 44 |
| [scripts/team-cloud-smoke.sh](/scripts/team-cloud-smoke.sh) | Shell Script | 17 | 1 | 9 | 27 |
| [scripts/team-cloud-spicedb-schema-ci.sh](/scripts/team-cloud-spicedb-schema-ci.sh) | Shell Script | 26 | 1 | 3 | 30 |
| [teamDoc/GADoc/P1-03-local-compose-stack.md](/teamDoc/GADoc/P1-03-local-compose-stack.md) | Markdown | 47 | 0 | 16 | 63 |
| [teamDoc/GADoc/P1-04-postgres-base-migrations.md](/teamDoc/GADoc/P1-04-postgres-base-migrations.md) | Markdown | 26 | 0 | 12 | 38 |
| [teamDoc/GADoc/P1-05-casdoor-oidc.md](/teamDoc/GADoc/P1-05-casdoor-oidc.md) | Markdown | 29 | 0 | 13 | 42 |
| [teamDoc/GADoc/P1-06-jwt-middleware.md](/teamDoc/GADoc/P1-06-jwt-middleware.md) | Markdown | 23 | 0 | 10 | 33 |
| [teamDoc/GADoc/P1-07-casdoor-sync-worker.md](/teamDoc/GADoc/P1-07-casdoor-sync-worker.md) | Markdown | 43 | 0 | 12 | 55 |
| [teamDoc/GADoc/P1-08-pat-service-account.md](/teamDoc/GADoc/P1-08-pat-service-account.md) | Markdown | 55 | 0 | 16 | 71 |
| [teamDoc/GADoc/P1-09-spicedb-client.md](/teamDoc/GADoc/P1-09-spicedb-client.md) | Markdown | 36 | 0 | 12 | 48 |
| [teamDoc/GADoc/P1-10-spicedb-schema-ci.md](/teamDoc/GADoc/P1-10-spicedb-schema-ci.md) | Markdown | 35 | 0 | 12 | 47 |
| [teamDoc/GADoc/P1-11-relationship-outbox.md](/teamDoc/GADoc/P1-11-relationship-outbox.md) | Markdown | 35 | 0 | 12 | 47 |
| [teamDoc/GADoc/P1-12-authz-middleware.md](/teamDoc/GADoc/P1-12-authz-middleware.md) | Markdown | 41 | 0 | 12 | 53 |
| [teamDoc/GADoc/P1-13-org-team-member-api.md](/teamDoc/GADoc/P1-13-org-team-member-api.md) | Markdown | 40 | 0 | 14 | 54 |
| [teamDoc/GADoc/P1-14-audit-baseline.md](/teamDoc/GADoc/P1-14-audit-baseline.md) | Markdown | 42 | 0 | 12 | 54 |
| [teamDoc/GADoc/P1-15-minio-manifest.md](/teamDoc/GADoc/P1-15-minio-manifest.md) | Markdown | 39 | 0 | 12 | 51 |
| [teamDoc/GADoc/P1-16-web-login-shell.md](/teamDoc/GADoc/P1-16-web-login-shell.md) | Markdown | 33 | 0 | 12 | 45 |
| [teamDoc/GADoc/P1-17-web-admin-pages.md](/teamDoc/GADoc/P1-17-web-admin-pages.md) | Markdown | 38 | 0 | 12 | 50 |
| [teamDoc/GADoc/P1-18-permission-explorer-minimal.md](/teamDoc/GADoc/P1-18-permission-explorer-minimal.md) | Markdown | 43 | 0 | 18 | 61 |
| [teamDoc/GADoc/P1-19-platform-foundation-tests.md](/teamDoc/GADoc/P1-19-platform-foundation-tests.md) | Markdown | 32 | 0 | 15 | 47 |
| [teamDoc/GADoc/P1-20-platform-security-negative.md](/teamDoc/GADoc/P1-20-platform-security-negative.md) | Markdown | 37 | 0 | 14 | 51 |
| [teamDoc/GADoc/P1-21-observability-baseline.md](/teamDoc/GADoc/P1-21-observability-baseline.md) | Markdown | 33 | 0 | 12 | 45 |
| [teamDoc/GADoc/P1-22-foundation-deployment-docs.md](/teamDoc/GADoc/P1-22-foundation-deployment-docs.md) | Markdown | 113 | 0 | 44 | 157 |
| [teamDoc/GADoc/P2-01-memory-migrations.md](/teamDoc/GADoc/P2-01-memory-migrations.md) | Markdown | 41 | 0 | 19 | 60 |
| [teamDoc/GADoc/P2-02-memory-query-layer.md](/teamDoc/GADoc/P2-02-memory-query-layer.md) | Markdown | 38 | 0 | 12 | 50 |
| [teamDoc/GADoc/P2-03-memory-crud-api.md](/teamDoc/GADoc/P2-03-memory-crud-api.md) | Markdown | 48 | 0 | 14 | 62 |
| [teamDoc/GADoc/P2-04-prefetch-pipeline.md](/teamDoc/GADoc/P2-04-prefetch-pipeline.md) | Markdown | 29 | 0 | 12 | 41 |
| [teamDoc/GADoc/P2-05-memory-relationships.md](/teamDoc/GADoc/P2-05-memory-relationships.md) | Markdown | 36 | 0 | 14 | 50 |
| [teamDoc/GADoc/P2-06-embedding-worker.md](/teamDoc/GADoc/P2-06-embedding-worker.md) | Markdown | 37 | 0 | 12 | 49 |
| [teamDoc/GADoc/P2-07-memory-extraction-worker.md](/teamDoc/GADoc/P2-07-memory-extraction-worker.md) | Markdown | 41 | 0 | 12 | 53 |
| [teamDoc/GADoc/P2-08-review-queue-api.md](/teamDoc/GADoc/P2-08-review-queue-api.md) | Markdown | 45 | 0 | 14 | 59 |
| [teamDoc/GADoc/P2-09-duplicate-conflict-detector.md](/teamDoc/GADoc/P2-09-duplicate-conflict-detector.md) | Markdown | 38 | 0 | 12 | 50 |
| [teamDoc/GADoc/P2-10-pii-secret-detector.md](/teamDoc/GADoc/P2-10-pii-secret-detector.md) | Markdown | 36 | 0 | 12 | 48 |
| [teamDoc/GADoc/P2-11-team-memory-provider.md](/teamDoc/GADoc/P2-11-team-memory-provider.md) | Markdown | 42 | 0 | 14 | 56 |
| [teamDoc/GADoc/P2-12-memory-tools.md](/teamDoc/GADoc/P2-12-memory-tools.md) | Markdown | 47 | 0 | 14 | 61 |
| [teamDoc/GADoc/P2-13-sync-turn-observation.md](/teamDoc/GADoc/P2-13-sync-turn-observation.md) | Markdown | 38 | 0 | 12 | 50 |
| [teamDoc/GADoc/P2-14-aiagent-team-context.md](/teamDoc/GADoc/P2-14-aiagent-team-context.md) | Markdown | 31 | 0 | 12 | 43 |
| [teamDoc/GADoc/P2-15-api-server-identity-headers.md](/teamDoc/GADoc/P2-15-api-server-identity-headers.md) | Markdown | 41 | 0 | 14 | 55 |
| [teamDoc/GADoc/P2-16-gateway-identity-resolver.md](/teamDoc/GADoc/P2-16-gateway-identity-resolver.md) | Markdown | 59 | 0 | 18 | 77 |
| [teamDoc/GADoc/P2-17-web-chat-entry.md](/teamDoc/GADoc/P2-17-web-chat-entry.md) | Markdown | 51 | 0 | 23 | 74 |
| [teamDoc/GADoc/P2-18-cloud-session-history.md](/teamDoc/GADoc/P2-18-cloud-session-history.md) | Markdown | 59 | 0 | 24 | 83 |
| [teamDoc/GADoc/P2-19-runtime-event-bridge.md](/teamDoc/GADoc/P2-19-runtime-event-bridge.md) | Markdown | 42 | 0 | 18 | 60 |
| [teamDoc/GADoc/P2-20-isolation-test-suite.md](/teamDoc/GADoc/P2-20-isolation-test-suite.md) | Markdown | 35 | 0 | 15 | 50 |
| [teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json](/teamDoc/GADoc/artifacts/p2-isolation-suite-v0.json) | JSON | 31 | 0 | 1 | 32 |
| [teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json](/teamDoc/GADoc/artifacts/platform-foundation-smoke-v0.json) | JSON | 127 | 0 | 1 | 128 |
| [teamDoc/GALog/2026-05-22-p1-03-local-compose-stack.md](/teamDoc/GALog/2026-05-22-p1-03-local-compose-stack.md) | Markdown | 53 | 0 | 12 | 65 |
| [teamDoc/GALog/2026-05-22-p1-04-postgres-base-migrations.md](/teamDoc/GALog/2026-05-22-p1-04-postgres-base-migrations.md) | Markdown | 48 | 0 | 12 | 60 |
| [teamDoc/GALog/2026-05-22-p1-05-casdoor-oidc.md](/teamDoc/GALog/2026-05-22-p1-05-casdoor-oidc.md) | Markdown | 48 | 0 | 12 | 60 |
| [teamDoc/GALog/2026-05-22-p1-06-jwt-middleware.md](/teamDoc/GALog/2026-05-22-p1-06-jwt-middleware.md) | Markdown | 49 | 0 | 14 | 63 |
| [teamDoc/GALog/2026-05-22-p1-07-casdoor-sync-worker.md](/teamDoc/GALog/2026-05-22-p1-07-casdoor-sync-worker.md) | Markdown | 38 | 0 | 9 | 47 |
| [teamDoc/GALog/2026-05-22-p1-08-pat-service-account.md](/teamDoc/GALog/2026-05-22-p1-08-pat-service-account.md) | Markdown | 32 | 0 | 9 | 41 |
| [teamDoc/GALog/2026-05-22-p1-09-spicedb-client.md](/teamDoc/GALog/2026-05-22-p1-09-spicedb-client.md) | Markdown | 26 | 0 | 7 | 33 |
| [teamDoc/GALog/2026-05-22-p1-10-spicedb-schema-ci.md](/teamDoc/GALog/2026-05-22-p1-10-spicedb-schema-ci.md) | Markdown | 29 | 0 | 9 | 38 |
| [teamDoc/GALog/2026-05-22-p1-11-relationship-outbox.md](/teamDoc/GALog/2026-05-22-p1-11-relationship-outbox.md) | Markdown | 25 | 0 | 7 | 32 |
| [teamDoc/GALog/2026-05-22-p1-12-authz-middleware.md](/teamDoc/GALog/2026-05-22-p1-12-authz-middleware.md) | Markdown | 28 | 0 | 9 | 37 |
| [teamDoc/GALog/2026-05-22-p1-13-org-team-member-api.md](/teamDoc/GALog/2026-05-22-p1-13-org-team-member-api.md) | Markdown | 25 | 0 | 7 | 32 |
| [teamDoc/GALog/2026-05-22-p1-14-audit-baseline.md](/teamDoc/GALog/2026-05-22-p1-14-audit-baseline.md) | Markdown | 24 | 0 | 7 | 31 |
| [teamDoc/GALog/2026-05-22-p1-15-minio-manifest.md](/teamDoc/GALog/2026-05-22-p1-15-minio-manifest.md) | Markdown | 25 | 0 | 7 | 32 |
| [teamDoc/GALog/2026-05-22-p1-16-web-login-shell.md](/teamDoc/GALog/2026-05-22-p1-16-web-login-shell.md) | Markdown | 21 | 0 | 7 | 28 |
| [teamDoc/GALog/2026-05-22-p1-17-web-admin-pages.md](/teamDoc/GALog/2026-05-22-p1-17-web-admin-pages.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p1-18-permission-explorer-minimal.md](/teamDoc/GALog/2026-05-22-p1-18-permission-explorer-minimal.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p1-19-platform-foundation-tests.md](/teamDoc/GALog/2026-05-22-p1-19-platform-foundation-tests.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p1-20-platform-security-negative.md](/teamDoc/GALog/2026-05-22-p1-20-platform-security-negative.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p1-21-observability-baseline.md](/teamDoc/GALog/2026-05-22-p1-21-observability-baseline.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p1-22-foundation-deployment-docs.md](/teamDoc/GALog/2026-05-22-p1-22-foundation-deployment-docs.md) | Markdown | 22 | 0 | 7 | 29 |
| [teamDoc/GALog/2026-05-22-p1-estimate-reconciliation.md](/teamDoc/GALog/2026-05-22-p1-estimate-reconciliation.md) | Markdown | 12 | 0 | 7 | 19 |
| [teamDoc/GALog/2026-05-22-p2-01-memory-migrations.md](/teamDoc/GALog/2026-05-22-p2-01-memory-migrations.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-02-memory-query-layer.md](/teamDoc/GALog/2026-05-22-p2-02-memory-query-layer.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-03-memory-crud-api.md](/teamDoc/GALog/2026-05-22-p2-03-memory-crud-api.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-04-prefetch-pipeline.md](/teamDoc/GALog/2026-05-22-p2-04-prefetch-pipeline.md) | Markdown | 22 | 0 | 7 | 29 |
| [teamDoc/GALog/2026-05-22-p2-05-memory-relationships.md](/teamDoc/GALog/2026-05-22-p2-05-memory-relationships.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-06-embedding-worker.md](/teamDoc/GALog/2026-05-22-p2-06-embedding-worker.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-07-memory-extraction-worker.md](/teamDoc/GALog/2026-05-22-p2-07-memory-extraction-worker.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-08-review-queue-api.md](/teamDoc/GALog/2026-05-22-p2-08-review-queue-api.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-09-duplicate-conflict-detector.md](/teamDoc/GALog/2026-05-22-p2-09-duplicate-conflict-detector.md) | Markdown | 22 | 0 | 7 | 29 |
| [teamDoc/GALog/2026-05-22-p2-10-pii-secret-detector.md](/teamDoc/GALog/2026-05-22-p2-10-pii-secret-detector.md) | Markdown | 22 | 0 | 7 | 29 |
| [teamDoc/GALog/2026-05-22-p2-11-team-memory-provider.md](/teamDoc/GALog/2026-05-22-p2-11-team-memory-provider.md) | Markdown | 23 | 0 | 7 | 30 |
| [teamDoc/GALog/2026-05-22-p2-12-memory-tools.md](/teamDoc/GALog/2026-05-22-p2-12-memory-tools.md) | Markdown | 24 | 0 | 7 | 31 |
| [teamDoc/GALog/2026-05-22-p2-13-sync-turn-observation.md](/teamDoc/GALog/2026-05-22-p2-13-sync-turn-observation.md) | Markdown | 30 | 0 | 7 | 37 |
| [teamDoc/GALog/2026-05-22-p2-14-aiagent-team-context.md](/teamDoc/GALog/2026-05-22-p2-14-aiagent-team-context.md) | Markdown | 25 | 0 | 7 | 32 |
| [teamDoc/GALog/2026-05-22-p2-15-api-server-identity-headers.md](/teamDoc/GALog/2026-05-22-p2-15-api-server-identity-headers.md) | Markdown | 28 | 0 | 7 | 35 |
| [teamDoc/GALog/2026-05-22-p2-16-gateway-identity-resolver.md](/teamDoc/GALog/2026-05-22-p2-16-gateway-identity-resolver.md) | Markdown | 39 | 0 | 10 | 49 |
| [teamDoc/GALog/2026-05-22-p2-17-web-chat-entry.md](/teamDoc/GALog/2026-05-22-p2-17-web-chat-entry.md) | Markdown | 36 | 0 | 10 | 46 |
| [teamDoc/GALog/2026-05-22-p2-18-cloud-session-history.md](/teamDoc/GALog/2026-05-22-p2-18-cloud-session-history.md) | Markdown | 33 | 0 | 10 | 43 |
| [teamDoc/GALog/2026-05-22-p2-19-runtime-event-bridge.md](/teamDoc/GALog/2026-05-22-p2-19-runtime-event-bridge.md) | Markdown | 33 | 0 | 10 | 43 |
| [teamDoc/GALog/2026-05-22-p2-20-isolation-test-suite.md](/teamDoc/GALog/2026-05-22-p2-20-isolation-test-suite.md) | Markdown | 30 | 0 | 10 | 40 |
| [team\_cloud/admin/\_\_init\_\_.py](/team_cloud/admin/__init__.py) | Python | 6 | 1 | 3 | 10 |
| [team\_cloud/admin/organizations.py](/team_cloud/admin/organizations.py) | Python | 87 | 3 | 19 | 109 |
| [team\_cloud/api.py](/team_cloud/api.py) | Python | 631 | 0 | 69 | 700 |
| [team\_cloud/audit.py](/team_cloud/audit.py) | Python | 49 | 1 | 7 | 57 |
| [team\_cloud/auth/\_\_init\_\_.py](/team_cloud/auth/__init__.py) | Python | 26 | 1 | 4 | 31 |
| [team\_cloud/auth/middleware.py](/team_cloud/auth/middleware.py) | Python | 65 | 1 | 16 | 82 |
| [team\_cloud/auth/oidc.py](/team_cloud/auth/oidc.py) | Python | 143 | 2 | 21 | 166 |
| [team\_cloud/auth/tokens.py](/team_cloud/auth/tokens.py) | Python | 405 | 2 | 51 | 458 |
| [team\_cloud/authz/\_\_init\_\_.py](/team_cloud/authz/__init__.py) | Python | 38 | 1 | 3 | 42 |
| [team\_cloud/authz/explain.py](/team_cloud/authz/explain.py) | Python | 90 | 1 | 15 | 106 |
| [team\_cloud/authz/middleware.py](/team_cloud/authz/middleware.py) | Python | 113 | 1 | 28 | 142 |
| [team\_cloud/authz/outbox.py](/team_cloud/authz/outbox.py) | Python | 184 | 1 | 30 | 215 |
| [team\_cloud/authz/schema\_ci.py](/team_cloud/authz/schema_ci.py) | Python | 181 | 2 | 35 | 218 |
| [team\_cloud/authz/spicedb.py](/team_cloud/authz/spicedb.py) | Python | 188 | 1 | 35 | 224 |
| [team\_cloud/chat.py](/team_cloud/chat.py) | Python | 155 | 3 | 19 | 177 |
| [team\_cloud/cloud\_sessions.py](/team_cloud/cloud_sessions.py) | Python | 201 | 3 | 25 | 229 |
| [team\_cloud/identity.py](/team_cloud/identity.py) | Python | 99 | 2 | 20 | 121 |
| [team\_cloud/memory/\_\_init\_\_.py](/team_cloud/memory/__init__.py) | Python | 65 | 1 | 3 | 69 |
| [team\_cloud/memory/detectors.py](/team_cloud/memory/detectors.py) | Python | 121 | 1 | 13 | 135 |
| [team\_cloud/memory/embedding.py](/team_cloud/memory/embedding.py) | Python | 181 | 1 | 25 | 207 |
| [team\_cloud/memory/extraction.py](/team_cloud/memory/extraction.py) | Python | 271 | 1 | 31 | 303 |
| [team\_cloud/memory/prefetch.py](/team_cloud/memory/prefetch.py) | Python | 78 | 1 | 16 | 95 |
| [team\_cloud/memory/provider.py](/team_cloud/memory/provider.py) | Python | 384 | 7 | 44 | 435 |
| [team\_cloud/memory/query.py](/team_cloud/memory/query.py) | Python | 183 | 1 | 27 | 211 |
| [team\_cloud/memory/relationships.py](/team_cloud/memory/relationships.py) | Python | 82 | 1 | 13 | 96 |
| [team\_cloud/memory/review.py](/team_cloud/memory/review.py) | Python | 144 | 3 | 18 | 165 |
| [team\_cloud/memory/safety.py](/team_cloud/memory/safety.py) | Python | 112 | 1 | 15 | 128 |
| [team\_cloud/memory/service.py](/team_cloud/memory/service.py) | Python | 159 | 2 | 25 | 186 |
| [team\_cloud/migrations.py](/team_cloud/migrations.py) | Python | 35 | 0 | 4 | 39 |
| [team\_cloud/observability.py](/team_cloud/observability.py) | Python | 37 | 1 | 7 | 45 |
| [team\_cloud/runtime\_events.py](/team_cloud/runtime_events.py) | Python | 101 | 1 | 18 | 120 |
| [team\_cloud/sql\_migrations/001\_schema\_v0.rollback.md](/team_cloud/sql_migrations/001_schema_v0.rollback.md) | Markdown | 35 | 0 | 5 | 40 |
| [team\_cloud/sql\_migrations/001\_schema\_v0.sql](/team_cloud/sql_migrations/001_schema_v0.sql) | MS SQL | 345 | 0 | 28 | 373 |
| [team\_cloud/sql\_migrations/002\_memory\_runtime\_schema.rollback.md](/team_cloud/sql_migrations/002_memory_runtime_schema.rollback.md) | Markdown | 17 | 0 | 6 | 23 |
| [team\_cloud/sql\_migrations/002\_memory\_runtime\_schema.sql](/team_cloud/sql_migrations/002_memory_runtime_schema.sql) | MS SQL | 24 | 1 | 11 | 36 |
| [team\_cloud/storage/\_\_init\_\_.py](/team_cloud/storage/__init__.py) | Python | 2 | 1 | 3 | 6 |
| [team\_cloud/storage/minio.py](/team_cloud/storage/minio.py) | Python | 172 | 1 | 24 | 197 |
| [team\_cloud/sync/\_\_init\_\_.py](/team_cloud/sync/__init__.py) | Python | 12 | 1 | 3 | 16 |
| [team\_cloud/sync/casdoor.py](/team_cloud/sync/casdoor.py) | Python | 501 | 2 | 60 | 563 |
| [team\_cloud/worker.py](/team_cloud/worker.py) | Python | 15 | 0 | 5 | 20 |
| [tests/gateway/test\_api\_server\_team\_headers.py](/tests/gateway/test_api_server_team_headers.py) | Python | 119 | 0 | 28 | 147 |
| [tests/gateway/test\_gateway\_team\_identity\_resolver.py](/tests/gateway/test_gateway_team_identity_resolver.py) | Python | 183 | 0 | 42 | 225 |
| [tests/run\_agent/test\_memory\_provider\_init.py](/tests/run_agent/test_memory_provider_init.py) | Python | 65 | 0 | 15 | 80 |
| [tests/team\_cloud/test\_admin\_org\_api.py](/tests/team_cloud/test_admin_org_api.py) | Python | 79 | 0 | 21 | 100 |
| [tests/team\_cloud/test\_audit\_baseline.py](/tests/team_cloud/test_audit_baseline.py) | Python | 67 | 0 | 16 | 83 |
| [tests/team\_cloud/test\_authz\_middleware.py](/tests/team_cloud/test_authz_middleware.py) | Python | 85 | 0 | 32 | 117 |
| [tests/team\_cloud/test\_casdoor\_oidc.py](/tests/team_cloud/test_casdoor_oidc.py) | Python | 175 | 0 | 49 | 224 |
| [tests/team\_cloud/test\_casdoor\_sync\_worker.py](/tests/team_cloud/test_casdoor_sync_worker.py) | Python | 148 | 0 | 27 | 175 |
| [tests/team\_cloud/test\_cloud\_session\_history.py](/tests/team_cloud/test_cloud_session_history.py) | Python | 98 | 0 | 23 | 121 |
| [tests/team\_cloud/test\_deployment\_docs.py](/tests/team_cloud/test_deployment_docs.py) | Python | 23 | 0 | 11 | 34 |
| [tests/team\_cloud/test\_external\_identity\_resolver.py](/tests/team_cloud/test_external_identity_resolver.py) | Python | 96 | 0 | 17 | 113 |
| [tests/team\_cloud/test\_isolation\_suite.py](/tests/team_cloud/test_isolation_suite.py) | Python | 31 | 0 | 10 | 41 |
| [tests/team\_cloud/test\_jwt\_middleware.py](/tests/team_cloud/test_jwt_middleware.py) | Python | 75 | 0 | 29 | 104 |
| [tests/team\_cloud/test\_local\_compose\_stack.py](/tests/team_cloud/test_local_compose_stack.py) | Python | 140 | 0 | 34 | 174 |
| [tests/team\_cloud/test\_memory\_crud\_api.py](/tests/team_cloud/test_memory_crud_api.py) | Python | 89 | 0 | 21 | 110 |
| [tests/team\_cloud/test\_memory\_duplicate\_conflict\_detector.py](/tests/team_cloud/test_memory_duplicate_conflict_detector.py) | Python | 114 | 0 | 27 | 141 |
| [tests/team\_cloud/test\_memory\_embedding\_worker.py](/tests/team_cloud/test_memory_embedding_worker.py) | Python | 157 | 0 | 20 | 177 |
| [tests/team\_cloud/test\_memory\_extraction\_worker.py](/tests/team_cloud/test_memory_extraction_worker.py) | Python | 143 | 0 | 19 | 162 |
| [tests/team\_cloud/test\_memory\_migrations.py](/tests/team_cloud/test_memory_migrations.py) | Python | 24 | 0 | 10 | 34 |
| [tests/team\_cloud/test\_memory\_observations\_api.py](/tests/team_cloud/test_memory_observations_api.py) | Python | 93 | 0 | 13 | 106 |
| [tests/team\_cloud/test\_memory\_pii\_secret\_detector.py](/tests/team_cloud/test_memory_pii_secret_detector.py) | Python | 105 | 0 | 23 | 128 |
| [tests/team\_cloud/test\_memory\_prefetch\_pipeline.py](/tests/team_cloud/test_memory_prefetch_pipeline.py) | Python | 104 | 0 | 17 | 121 |
| [tests/team\_cloud/test\_memory\_query\_layer.py](/tests/team_cloud/test_memory_query_layer.py) | Python | 130 | 0 | 17 | 147 |
| [tests/team\_cloud/test\_memory\_relationships.py](/tests/team_cloud/test_memory_relationships.py) | Python | 96 | 0 | 17 | 113 |
| [tests/team\_cloud/test\_memory\_review\_api.py](/tests/team_cloud/test_memory_review_api.py) | Python | 96 | 0 | 19 | 115 |
| [tests/team\_cloud/test\_minio\_manifest.py](/tests/team_cloud/test_minio_manifest.py) | Python | 75 | 0 | 22 | 97 |
| [tests/team\_cloud/test\_observability\_baseline.py](/tests/team_cloud/test_observability_baseline.py) | Python | 32 | 0 | 13 | 45 |
| [tests/team\_cloud/test\_pat\_service\_accounts.py](/tests/team_cloud/test_pat_service_accounts.py) | Python | 146 | 0 | 29 | 175 |
| [tests/team\_cloud/test\_permission\_explorer\_minimal.py](/tests/team_cloud/test_permission_explorer_minimal.py) | Python | 76 | 0 | 20 | 96 |
| [tests/team\_cloud/test\_platform\_foundation\_suite.py](/tests/team_cloud/test_platform_foundation_suite.py) | Python | 82 | 0 | 20 | 102 |
| [tests/team\_cloud/test\_platform\_security\_negative.py](/tests/team_cloud/test_platform_security_negative.py) | Python | 112 | 0 | 26 | 138 |
| [tests/team\_cloud/test\_postgres\_migrations.py](/tests/team_cloud/test_postgres_migrations.py) | Python | 83 | 0 | 28 | 111 |
| [tests/team\_cloud/test\_relationship\_outbox.py](/tests/team_cloud/test_relationship_outbox.py) | Python | 120 | 0 | 25 | 145 |
| [tests/team\_cloud/test\_runtime\_event\_bridge.py](/tests/team_cloud/test_runtime_event_bridge.py) | Python | 88 | 0 | 22 | 110 |
| [tests/team\_cloud/test\_spicedb\_client.py](/tests/team_cloud/test_spicedb_client.py) | Python | 141 | 0 | 28 | 169 |
| [tests/team\_cloud/test\_spicedb\_schema\_ci.py](/tests/team_cloud/test_spicedb_schema_ci.py) | Python | 39 | 0 | 19 | 58 |
| [tests/team\_cloud/test\_team\_memory\_provider.py](/tests/team_cloud/test_team_memory_provider.py) | Python | 154 | 0 | 27 | 181 |
| [tests/team\_cloud/test\_team\_memory\_provider\_tools.py](/tests/team_cloud/test_team_memory_provider_tools.py) | Python | 98 | 0 | 27 | 125 |
| [tests/team\_cloud/test\_web\_admin\_pages.py](/tests/team_cloud/test_web_admin_pages.py) | Python | 69 | 0 | 19 | 88 |
| [tests/team\_cloud/test\_web\_chat\_entry.py](/tests/team_cloud/test_web_chat_entry.py) | Python | 98 | 0 | 27 | 125 |
| [tests/team\_cloud/test\_web\_login\_shell.py](/tests/team_cloud/test_web_login_shell.py) | Python | 24 | 0 | 10 | 34 |

[Summary](results.md) / [Details](details.md) / [Diff Summary](diff.md) / Diff Details