-- P2-01 memory runtime schema refinements.

alter table memory_items
  add column if not exists memory_type text not null default 'fact'
    check (memory_type in ('fact', 'preference', 'procedure', 'constraint', 'summary'));

alter table memory_items
  add column if not exists source_event_id uuid references memory_events(id) on delete set null;

alter table memory_observations
  add column if not exists extraction_trace jsonb not null default '{}'::jsonb;

alter table memory_observations
  add column if not exists confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1));

alter table memory_review_items
  add column if not exists review_kind text not null default 'team_candidate'
    check (review_kind in ('team_candidate', 'pii', 'duplicate', 'conflict'));

alter table memory_review_items
  add column if not exists candidate_payload jsonb not null default '{}'::jsonb;

alter table memory_review_items
  add column if not exists confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1));

create index if not exists idx_memory_items_scope_type_status
  on memory_items (org_id, scope, memory_type, status, sensitivity);

create index if not exists idx_memory_review_pending_kind
  on memory_review_items (org_id, status, review_kind, created_at)
  where status = 'pending';

create index if not exists idx_memory_observations_pending
  on memory_observations (org_id, status, created_at)
  where status in ('pending', 'processing');
