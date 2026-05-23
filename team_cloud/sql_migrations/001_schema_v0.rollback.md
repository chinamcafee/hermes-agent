# Rollback note for 001_schema_v0.sql

This migration creates the initial Team Cloud PostgreSQL schema promoted from
`teamDoc/GADoc/artifacts/postgres/001_schema_v0.sql`.

Rollback is destructive and must only be used for local development or a failed
pre-GA bootstrap before any customer data exists. Drop dependent objects in the
reverse order of creation, then drop the `vector` and `pgcrypto` extensions only
when no other schema uses them.

Minimum local rollback shape:

```sql
drop table if exists audit_events cascade;
drop table if exists object_manifests cascade;
drop table if exists restore_jobs cascade;
drop table if exists backup_jobs cascade;
drop table if exists backup_policies cascade;
drop table if exists permission_cache cascade;
drop table if exists spicedb_outbox cascade;
drop table if exists memory_review_items cascade;
drop table if exists memory_observations cascade;
drop table if exists memory_events cascade;
drop table if exists memory_embeddings cascade;
drop table if exists memory_items cascade;
drop table if exists cloud_tool_calls cascade;
drop table if exists cloud_messages cascade;
drop table if exists cloud_sessions cascade;
drop table if exists api_tokens cascade;
drop table if exists service_accounts cascade;
drop table if exists external_identities cascade;
drop table if exists projects cascade;
drop table if exists teams cascade;
drop table if exists members cascade;
drop table if exists organizations cascade;
drop table if exists team_cloud_users cascade;
drop extension if exists vector;
drop extension if exists pgcrypto;
```
