package postgres

const SchemaSQL = `
create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists tcg_organizations (
  id text primary key,
  slug text not null unique,
  name text not null,
  status text not null default 'active'
    check (status in ('active', 'suspended', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists tcg_members (
  id text primary key,
  org_id text not null references tcg_organizations(id) on delete cascade,
  user_id text not null,
  email text not null default '',
  display_name text not null default '',
  role text not null default 'member',
  password_hash text not null default '',
  status text not null default 'invited'
    check (status in ('invited', 'active', 'suspended', 'removed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, user_id)
);

create table if not exists tcg_memory_items (
  id text primary key,
  org_id text not null references tcg_organizations(id) on delete cascade,
  scope text not null check (scope = 'team_shared'),
  subject_member_id text not null default '',
  team_id text not null default '',
  project_id text not null default '',
  status text not null default 'active'
    check (status in ('active', 'pending_review', 'archived', 'deleted', 'rejected')),
  sensitivity text not null default 'normal'
    check (sensitivity in ('normal', 'pii', 'secret', 'restricted')),
  memory_type text not null default 'fact',
  source_type text not null default ''
    check (source_type in ('', 'auto_extracted', 'admin_created')),
  source_member_id text not null default '',
  created_by_member_id text not null default '',
  content text not null,
  embedding vector(1536),
  version integer not null default 1 check (version > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (subject_member_id = '')
);

create index if not exists tcg_memory_items_lookup_idx
  on tcg_memory_items(org_id, scope, status, subject_member_id, team_id, project_id);

create index if not exists tcg_memory_items_embedding_hnsw_idx
  on tcg_memory_items using hnsw (embedding vector_cosine_ops)
  where embedding is not null;

create table if not exists tcg_memory_review_items (
  id text primary key,
  org_id text not null references tcg_organizations(id) on delete cascade,
  memory_id text not null references tcg_memory_items(id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'rejected', 'merged')),
  review_kind text not null default 'team_shared_memory',
  submitted_by_member_id text not null default '',
  reviewed_by_member_id text not null default '',
  reason text not null default '',
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create index if not exists tcg_memory_review_items_lookup_idx
  on tcg_memory_review_items(org_id, status, review_kind);

create table if not exists tcg_memory_observations (
  id text primary key,
  org_id text not null references tcg_organizations(id) on delete cascade,
  session_id text not null default '',
  member_id text not null default '',
  team_id text not null default '',
  project_id text not null default '',
  observation jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'extracted', 'ignored', 'error')),
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create table if not exists tcg_backup_policies (
  org_id text not null references tcg_organizations(id) on delete cascade,
  member_id text not null,
  cadence text not null default 'weekly'
    check (cadence in ('hourly', 'daily', 'weekly', 'monthly')),
  enabled boolean not null default false,
  retention_count integer not null default 4 check (retention_count > 0),
  last_run_at timestamptz,
  next_run_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (org_id, member_id)
);

create table if not exists tcg_audit_events (
  id text primary key,
  org_id text not null default '',
  actor_id text not null default '',
  action text not null,
  resource text not null default '',
  decision text not null default 'allowed',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists tcg_audit_events_lookup_idx
  on tcg_audit_events(org_id, created_at desc);

create table if not exists tcg_relationships (
  idempotency_key text primary key,
  org_id text not null,
  resource_type text not null,
  resource_id text not null,
  relation text not null,
  subject_type text not null,
  subject_id text not null,
  created_at timestamptz not null default now()
);

create index if not exists tcg_relationships_check_idx
  on tcg_relationships(org_id, resource_type, resource_id, subject_type, subject_id);

create table if not exists tcg_backup_jobs (
  id text primary key,
  org_id text not null,
  member_id text not null,
  status text not null,
  object_key text not null,
  object_uploaded boolean not null default false,
  checksum_sha256 text not null,
  item_count integer not null default 0,
  manifest jsonb not null default '{}'::jsonb,
  items jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists tcg_restore_previews (
  backup_id text not null references tcg_backup_jobs(id) on delete cascade,
  member_id text not null,
  mode text not null,
  create_count integer not null default 0,
  skip_count integer not null default 0,
  created_at timestamptz not null default now(),
  primary key (backup_id, member_id, mode)
);

create table if not exists tcg_org_exports (
  id text primary key,
  org_id text not null,
  status text not null,
  team_shared_count integer not null default 0,
  personal_count integer not null default 0,
  manifest jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists tcg_deletion_requests (
  id text primary key,
  org_id text not null,
  target_member_id text not null,
  requested_by text not null default '',
  deletion_scope text not null,
  reason text not null default '',
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  executed_at timestamptz
);

create table if not exists tcg_tool_policy_rules (
  org_id text not null,
  tool_name text not null,
  risk_level text not null default '*',
  decision text not null,
  updated_by text not null default '',
  updated_at timestamptz not null default now(),
  primary key (org_id, tool_name, risk_level)
);

create table if not exists tcg_cloud_sessions (
  id text primary key,
  org_id text not null,
  team_id text not null,
  project_id text not null default '',
  owner_member_id text not null default '',
  title text not null default '',
  status text not null default 'active',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists tcg_runtime_events (
  id text primary key,
  org_id text not null,
  session_id text not null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists tcg_team_souls (
  org_id text not null references tcg_organizations(id) on delete cascade,
  team_id text not null,
  content text not null,
  version integer not null default 1 check (version > 0),
  checksum_sha256 text not null,
  updated_by text not null default '',
  updated_at timestamptz not null default now(),
  primary key (org_id, team_id)
);

alter table if exists tcg_backup_policies
  add column if not exists last_run_at timestamptz;

alter table if exists tcg_backup_policies
  add column if not exists next_run_at timestamptz;

alter table if exists tcg_members
  add column if not exists password_hash text not null default '';

alter table if exists tcg_memory_items
  add column if not exists source_type text not null default '';

alter table if exists tcg_memory_items
  add column if not exists source_member_id text not null default '';

alter table if exists tcg_memory_items
  add column if not exists created_by_member_id text not null default '';

create unique index if not exists tcg_members_one_super_admin_idx
  on tcg_members((role))
  where role = 'super_admin' and status <> 'removed';

drop table if exists tcg_teams cascade;
`
