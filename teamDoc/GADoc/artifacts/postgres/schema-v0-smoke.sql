begin;

insert into team_cloud_users (id, casdoor_subject, primary_email, display_name)
values ('00000000-0000-0000-0000-000000000001', 'casdoor-admin', 'admin@example.com', 'Admin');

insert into organizations (id, casdoor_org, slug, name)
values ('10000000-0000-0000-0000-000000000001', 'built-in', 'org-local', 'Local Org');

insert into teams (id, org_id, slug, name)
values ('20000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'default', 'Default Team');

insert into members (id, org_id, user_id, status, default_team_id, joined_at)
values (
  '30000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  '00000000-0000-0000-0000-000000000001',
  'active',
  '20000000-0000-0000-0000-000000000001',
  now()
);

insert into projects (id, org_id, team_id, slug, name)
values (
  '40000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  'default',
  'Default Project'
);

insert into cloud_sessions (id, org_id, team_id, project_id, owner_member_id, title)
values (
  '50000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '40000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  'Smoke Session'
);

insert into memory_items (
  id, org_id, scope, subject_member_id, status, sensitivity,
  content, normalized_content, checksum_sha256, created_by_member_id
) values (
  '60000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  'personal',
  '30000000-0000-0000-0000-000000000001',
  'active',
  'normal',
  'Personal memory smoke',
  'personal memory smoke',
  repeat('a', 64),
  '30000000-0000-0000-0000-000000000001'
);

insert into memory_items (
  id, org_id, scope, team_id, status, sensitivity,
  content, normalized_content, checksum_sha256, created_by_member_id
) values (
  '60000000-0000-0000-0000-000000000002',
  '10000000-0000-0000-0000-000000000001',
  'team_shared',
  '20000000-0000-0000-0000-000000000001',
  'pending_review',
  'normal',
  'Team memory smoke',
  'team memory smoke',
  repeat('b', 64),
  '30000000-0000-0000-0000-000000000001'
);

insert into memory_embeddings (org_id, memory_id, embedding_model, embedding)
values (
  '10000000-0000-0000-0000-000000000001',
  '60000000-0000-0000-0000-000000000001',
  'smoke-1536',
  array_fill(0.0::real, array[1536])::vector
);

insert into memory_events (org_id, memory_id, actor_member_id, event_type)
values (
  '10000000-0000-0000-0000-000000000001',
  '60000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  'create'
);

insert into memory_observations (org_id, session_id, member_id, team_id, observation)
values (
  '10000000-0000-0000-0000-000000000001',
  '50000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  '20000000-0000-0000-0000-000000000001',
  '{"text": "remember the smoke test"}'
);

insert into object_manifests (
  id, org_id, owner_member_id, bucket, object_key, object_type,
  checksum_sha256, encryption_key_id, size_bytes
) values (
  '70000000-0000-0000-0000-000000000001',
  '10000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  'hermes-personal-backups',
  'org/10000000-0000-0000-0000-000000000001/member/30000000-0000-0000-0000-000000000001/personal-memory/2026/05/smoke.jsonl.enc',
  'personal_backup',
  repeat('c', 64),
  'local-dev-key',
  128
);

insert into backup_policies (org_id, member_id, cadence, enabled)
values (
  '10000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  'weekly',
  true
);

insert into backup_jobs (org_id, member_id, object_manifest_id, status, item_count, checksum_sha256)
values (
  '10000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  '70000000-0000-0000-0000-000000000001',
  'succeeded',
  1,
  repeat('c', 64)
);

insert into spicedb_outbox (
  org_id, aggregate_type, aggregate_id, idempotency_key, operation, relationships
) values (
  '10000000-0000-0000-0000-000000000001',
  'memory',
  '60000000-0000-0000-0000-000000000002',
  'memory-team-shared-smoke',
  'create',
  '[{"resource":"memory:memory_team_shared","relation":"parent_team","subject":"team:team_default"}]'::jsonb
);

insert into audit_events (
  org_id, actor_member_id, actor_type, action, resource_type, resource_id, decision
) values (
  '10000000-0000-0000-0000-000000000001',
  '30000000-0000-0000-0000-000000000001',
  'human',
  'memory.create',
  'memory',
  '60000000-0000-0000-0000-000000000001',
  'recorded'
);

do $$
begin
  insert into memory_items (
    org_id, scope, status, sensitivity, content, normalized_content, checksum_sha256
  ) values (
    '10000000-0000-0000-0000-000000000001',
    'personal',
    'active',
    'normal',
    'invalid',
    'invalid',
    repeat('d', 64)
  );
  raise exception 'expected personal memory scope constraint to fail';
exception
  when check_violation then null;
end $$;

select extversion as vector_version
from pg_extension
where extname = 'vector';

rollback;
