create extension if not exists pgcrypto;
create extension if not exists vector;

create table if not exists team_cloud_users (
  id uuid primary key default gen_random_uuid(),
  casdoor_subject text not null unique,
  primary_email text not null,
  display_name text not null default '',
  avatar_url text not null default '',
  status text not null default 'active'
    check (status in ('active', 'suspended', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists organizations (
  id uuid primary key default gen_random_uuid(),
  casdoor_org text unique,
  slug text not null unique,
  name text not null,
  plan text not null default 'team',
  status text not null default 'active'
    check (status in ('active', 'suspended', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists members (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null references team_cloud_users(id) on delete restrict,
  status text not null default 'active'
    check (status in ('invited', 'active', 'suspended', 'removed')),
  default_team_id uuid,
  joined_at timestamptz,
  removed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, user_id)
);

create table if not exists teams (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  slug text not null,
  name text not null,
  visibility text not null default 'private'
    check (visibility in ('private', 'org_visible')),
  status text not null default 'active'
    check (status in ('active', 'archived', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, slug)
);

alter table members
  add constraint members_default_team_fk
  foreign key (default_team_id) references teams(id)
  deferrable initially deferred;

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  team_id uuid not null references teams(id) on delete cascade,
  slug text not null,
  name text not null,
  status text not null default 'active'
    check (status in ('active', 'archived', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, team_id, slug)
);

create table if not exists external_identities (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  platform text not null,
  external_user_id text not null,
  external_team_id text,
  external_channel_id text,
  metadata jsonb not null default '{}'::jsonb,
  status text not null default 'active'
    check (status in ('active', 'revoked', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists service_accounts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  owner_member_id uuid not null references members(id) on delete restrict,
  name text not null,
  status text not null default 'active'
    check (status in ('active', 'suspended', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, name)
);

create table if not exists api_tokens (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  owner_member_id uuid references members(id) on delete cascade,
  service_account_id uuid references service_accounts(id) on delete cascade,
  token_hash bytea not null,
  scopes text[] not null default '{}',
  expires_at timestamptz,
  last_used_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  check (
    (owner_member_id is not null and service_account_id is null)
    or (owner_member_id is null and service_account_id is not null)
  )
);

create table if not exists cloud_sessions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  team_id uuid not null references teams(id) on delete cascade,
  project_id uuid not null references projects(id) on delete cascade,
  owner_member_id uuid references members(id) on delete set null,
  title text not null default '',
  source_platform text not null default 'web',
  status text not null default 'active'
    check (status in ('active', 'archived', 'deleted')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists cloud_messages (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  session_id uuid not null references cloud_sessions(id) on delete cascade,
  role text not null check (role in ('system', 'user', 'assistant', 'tool')),
  content jsonb not null,
  token_count integer,
  created_at timestamptz not null default now()
);

create table if not exists cloud_tool_calls (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  session_id uuid references cloud_sessions(id) on delete set null,
  actor_member_id uuid references members(id) on delete set null,
  tool_name text not null,
  risk_level text not null
    check (risk_level in ('safe', 'network', 'file_read', 'file_write', 'terminal', 'destructive')),
  decision text not null
    check (decision in ('allowed', 'denied', 'approval_required', 'approved', 'rejected', 'error')),
  input_redacted jsonb not null default '{}'::jsonb,
  output_redacted jsonb,
  error text,
  created_at timestamptz not null default now()
);

create table if not exists memory_items (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  scope text not null check (scope in ('personal', 'team_shared')),
  subject_member_id uuid references members(id) on delete cascade,
  team_id uuid references teams(id) on delete cascade,
  project_id uuid references projects(id) on delete set null,
  status text not null default 'active'
    check (status in ('active', 'pending_review', 'archived', 'deleted', 'rejected')),
  sensitivity text not null default 'normal'
    check (sensitivity in ('normal', 'pii', 'secret', 'restricted')),
  content text not null,
  normalized_content text not null,
  source_type text not null default 'conversation',
  source_ref jsonb not null default '{}'::jsonb,
  version integer not null default 1 check (version > 0),
  checksum_sha256 text not null,
  created_by_member_id uuid references members(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  check (
    (scope = 'personal' and subject_member_id is not null and team_id is null)
    or (scope = 'team_shared' and subject_member_id is null and team_id is not null)
  )
);

create table if not exists memory_embeddings (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  memory_id uuid not null references memory_items(id) on delete cascade,
  embedding_model text not null,
  embedding_dim integer not null default 1536 check (embedding_dim > 0),
  embedding vector(1536) not null,
  created_at timestamptz not null default now(),
  unique (memory_id, embedding_model)
);

create table if not exists memory_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  memory_id uuid references memory_items(id) on delete set null,
  actor_member_id uuid references members(id) on delete set null,
  event_type text not null
    check (event_type in ('create', 'update', 'read', 'promote', 'archive', 'delete', 'restore', 'reject')),
  event_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists memory_observations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  session_id uuid references cloud_sessions(id) on delete set null,
  member_id uuid references members(id) on delete set null,
  team_id uuid references teams(id) on delete set null,
  observation jsonb not null,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'extracted', 'ignored', 'error')),
  error text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create table if not exists memory_review_items (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  memory_id uuid references memory_items(id) on delete cascade,
  proposed_scope text not null check (proposed_scope in ('personal', 'team_shared')),
  reviewer_member_id uuid references members(id) on delete set null,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'rejected', 'merged')),
  reason text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create table if not exists spicedb_outbox (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  aggregate_type text not null,
  aggregate_id uuid not null,
  idempotency_key text not null unique,
  operation text not null check (operation in ('touch', 'create', 'delete')),
  relationships jsonb not null,
  status text not null default 'pending'
    check (status in ('pending', 'processing', 'applied', 'failed', 'dead_letter')),
  attempts integer not null default 0,
  last_error text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);

create table if not exists permission_cache (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  subject_ref text not null,
  resource_ref text not null,
  permission text not null,
  decision boolean not null,
  consistency_token text,
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  unique (org_id, subject_ref, resource_ref, permission)
);

create table if not exists backup_policies (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  cadence text not null default 'weekly'
    check (cadence in ('daily', 'weekly', 'monthly')),
  next_run_at timestamptz,
  retention_count integer not null default 8 check (retention_count > 0),
  enabled boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (org_id, member_id)
);

create table if not exists backup_jobs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  policy_id uuid references backup_policies(id) on delete set null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  object_manifest_id uuid,
  item_count integer not null default 0,
  checksum_sha256 text,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create table if not exists restore_jobs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  member_id uuid not null references members(id) on delete cascade,
  source_manifest_id uuid,
  mode text not null default 'preview_only'
    check (mode in ('preview_only', 'merge', 'overwrite', 'archive_current_then_restore')),
  status text not null default 'queued'
    check (status in ('queued', 'previewed', 'running', 'succeeded', 'failed', 'cancelled')),
  preview jsonb not null default '{}'::jsonb,
  error text,
  created_at timestamptz not null default now(),
  finished_at timestamptz
);

create table if not exists object_manifests (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references organizations(id) on delete cascade,
  owner_member_id uuid references members(id) on delete set null,
  bucket text not null,
  object_key text not null,
  object_type text not null
    check (object_type in ('personal_backup', 'org_export', 'attachment', 'document_source', 'restore_staging')),
  checksum_sha256 text not null,
  encryption_key_id text,
  size_bytes bigint not null check (size_bytes >= 0),
  status text not null default 'active'
    check (status in ('active', 'deleted', 'quarantined', 'staged')),
  created_at timestamptz not null default now(),
  deleted_at timestamptz,
  unique (bucket, object_key)
);

alter table backup_jobs
  add constraint backup_jobs_object_manifest_fk
  foreign key (object_manifest_id) references object_manifests(id)
  deferrable initially deferred;

alter table restore_jobs
  add constraint restore_jobs_source_manifest_fk
  foreign key (source_manifest_id) references object_manifests(id)
  deferrable initially deferred;

create table if not exists audit_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  actor_member_id uuid references members(id) on delete set null,
  actor_type text not null default 'system'
    check (actor_type in ('human', 'service_account', 'system')),
  action text not null,
  resource_type text not null,
  resource_id uuid,
  decision text not null default 'recorded'
    check (decision in ('allowed', 'denied', 'recorded', 'error')),
  request_id text,
  ip_address inet,
  user_agent text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_members_org_status on members (org_id, status);
create unique index if not exists idx_external_identities_unique_platform_user_team
  on external_identities (platform, external_user_id, coalesce(external_team_id, ''));
create index if not exists idx_teams_org_status on teams (org_id, status);
create index if not exists idx_projects_org_team_status on projects (org_id, team_id, status);
create index if not exists idx_sessions_org_project_status on cloud_sessions (org_id, project_id, status);
create index if not exists idx_memory_items_personal
  on memory_items (org_id, subject_member_id, status, sensitivity)
  where scope = 'personal';
create index if not exists idx_memory_items_team
  on memory_items (org_id, team_id, status, sensitivity)
  where scope = 'team_shared';
create index if not exists idx_memory_embeddings_hnsw
  on memory_embeddings using hnsw (embedding vector_cosine_ops);
create index if not exists idx_memory_events_org_memory_created on memory_events (org_id, memory_id, created_at desc);
create index if not exists idx_observations_status_created on memory_observations (status, created_at);
create index if not exists idx_spicedb_outbox_status_created on spicedb_outbox (status, created_at);
create index if not exists idx_object_manifests_org_type_status on object_manifests (org_id, object_type, status);
create index if not exists idx_audit_events_org_created on audit_events (org_id, created_at desc);
