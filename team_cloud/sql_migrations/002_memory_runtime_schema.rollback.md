# Rollback: 002_memory_runtime_schema.sql

This rollback is intended for local/dev use before data has been written through P2 memory APIs. For shared or production-like environments, prefer a forward migration that preserves data.

```sql
drop index if exists idx_memory_observations_pending;
drop index if exists idx_memory_review_pending_kind;
drop index if exists idx_memory_items_scope_type_status;

alter table memory_review_items
  drop column if exists confidence,
  drop column if exists candidate_payload,
  drop column if exists review_kind;

alter table memory_observations
  drop column if exists confidence,
  drop column if exists extraction_trace;

alter table memory_items
  drop column if exists source_event_id,
  drop column if exists memory_type;
```
