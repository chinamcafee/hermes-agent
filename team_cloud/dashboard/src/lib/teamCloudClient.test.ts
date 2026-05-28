import { buildBootstrapPayload, createTeamCloudClient } from './teamCloudClient';

describe('teamCloudClient', () => {
  it('builds the bootstrap payload expected by Dashboard V2', () => {
    expect(buildBootstrapPayload({
      teamName: 'Hermes Labs',
      adminEmail: 'owner@example.com',
      adminDisplayName: 'Owner Example',
      adminUserId: 'owner',
      adminPassword: 'correct horse battery staple'
    })).toEqual({
      org_slug: 'hermes-labs',
      org_name: 'Hermes Labs',
      admin_email: 'owner@example.com',
      admin_display_name: 'Owner Example',
      admin_user_id: 'owner',
      admin_password: 'correct horse battery staple'
    });
  });

  it('creates the initial team without bootstrap authentication', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: '',
      sessionToken: '',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ initialized: true }), {
          status: 201,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.createSuperAdmin({
      teamName: 'Hermes Labs',
      adminEmail: 'owner@example.com',
      adminDisplayName: 'Owner',
      adminUserId: 'owner',
      adminPassword: 'password'
    });

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/v1/bootstrap/super-admin');
    expect(calls[0].init?.method).toBe('POST');
    expect(calls[0].init?.headers).not.toMatchObject({
      Authorization: expect.any(String)
    });
    expect(JSON.parse(String(calls[0].init?.body))).toMatchObject({
      org_slug: 'hermes-labs',
      admin_user_id: 'owner'
    });
    expect(JSON.parse(String(calls[0].init?.body))).not.toHaveProperty('team_slug');
    expect(JSON.parse(String(calls[0].init?.body))).not.toHaveProperty('team_name');
  });

  it('logs in and creates members with dashboard session auth', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: 'http://localhost:8780/',
      sessionToken: 'hcs_session_token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ token: 'session-token', id: 'member-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.login({ orgId: 'hermes-labs', userId: 'owner', password: 'pw' });
    await client.createMember('hermes-labs', {
      email: 'admin@example.com',
      displayName: 'Admin',
      userId: 'admin',
      role: 'admin',
      password: 'pw'
    });
    await client.updateMember('hermes-labs', 'hermes-labs:admin', {
      email: 'ops-admin@example.com',
      displayName: 'Ops Admin'
    });

    expect(calls[0].url).toBe('http://localhost:8780/v1/auth/login');
    expect(calls[1].url).toBe('http://localhost:8780/api/organizations/hermes-labs/members');
    expect(calls[1].init?.method).toBe('POST');
    expect(calls[1].init?.headers).toMatchObject({
      Authorization: 'Bearer hcs_session_token'
    });
    expect(calls[2].url).toBe('http://localhost:8780/api/organizations/hermes-labs/members/hermes-labs%3Aadmin');
    expect(calls[2].init?.method).toBe('PATCH');
    expect(JSON.parse(String(calls[2].init?.body))).toEqual({
      email: 'ops-admin@example.com',
      display_name: 'Ops Admin'
    });
  });

  it('manages team memories with source labels and lifecycle actions', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: 'http://localhost:8780',
      sessionToken: 'hcs_session_token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ items: [], id: 'mem-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.listTeamMemories('hermes-labs', 'active');
    await client.createTeamMemory('hermes-labs', {
      content: '所有生产事故都要有明确 owner。',
      memoryType: 'policy',
      sensitivity: 'normal'
    });
    await client.updateMemory('mem-1', {
      content: '所有生产事故都要在首响阶段明确 owner。',
      memoryType: 'policy',
      sensitivity: 'normal'
    });
    await client.disableMemory('mem-1');
    await client.deleteMemory('mem-1');

    expect(calls[0].url).toBe('http://localhost:8780/v1/memory?org_id=hermes-labs&scope=team_shared&status=active');
    expect(calls[1].url).toBe('http://localhost:8780/v1/memory');
    expect(calls[1].init?.method).toBe('POST');
    expect(JSON.parse(String(calls[1].init?.body))).toMatchObject({
      org_id: 'hermes-labs',
      scope: 'team_shared',
      status: 'active',
      source_type: 'admin_created',
      content: '所有生产事故都要有明确 owner。',
      memory_type: 'policy',
      sensitivity: 'normal'
    });
    expect(calls[2].url).toBe('http://localhost:8780/v1/memory/mem-1');
    expect(calls[2].init?.method).toBe('PATCH');
    expect(calls[3].url).toBe('http://localhost:8780/v1/memory/mem-1/disable');
    expect(calls[3].init?.method).toBe('POST');
    expect(calls[4].url).toBe('http://localhost:8780/v1/memory/mem-1');
    expect(calls[4].init?.method).toBe('DELETE');
    expect(calls[4].init?.headers).toMatchObject({
      Authorization: 'Bearer hcs_session_token'
    });
  });

  it('previews then restores team memory backups instead of using personal backup endpoints', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: 'http://localhost:8780',
      sessionToken: 'hcs_session_token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ items: [], id: 'backup-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.getTeamBackupPolicy('hermes-labs');
    await client.upsertTeamBackupPolicy({
      org_id: 'hermes-labs',
      cadence: 'daily',
      enabled: true,
      retention_count: 7
    });
    await client.listTeamBackups('hermes-labs');
    await client.runTeamBackup({ org_id: 'hermes-labs' });
    await client.restoreTeamBackup('backup-1', { org_id: 'hermes-labs', mode: 'merge' });

    expect(calls.map(call => call.url)).toEqual([
      'http://localhost:8780/v1/team-memory-backup-policy?org_id=hermes-labs',
      'http://localhost:8780/v1/team-memory-backup-policy',
      'http://localhost:8780/v1/backups/team?org_id=hermes-labs',
      'http://localhost:8780/v1/backups/team/run',
      'http://localhost:8780/v1/backups/team/backup-1/restore-preview',
      'http://localhost:8780/v1/backups/team/backup-1/restore-execute'
    ]);
    expect(calls.some(call => String(call.init?.body ?? '').includes('member_id'))).toBe(false);
  });

  it('uses team soul backup policy, history, run, preview and restore endpoints', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: 'http://localhost:8780',
      sessionToken: 'hcs_session_token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ items: [], id: 'soul-backup-1' }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.getTeamSoulBackupPolicy('hermes-labs');
    await client.upsertTeamSoulBackupPolicy({
      org_id: 'hermes-labs',
      cadence: 'weekly',
      enabled: true,
      retention_count: 3
    });
    await client.listTeamSoulBackups('hermes-labs');
    await client.runTeamSoulBackup({ org_id: 'hermes-labs' });
    await client.restoreTeamSoulBackup('soul-backup-1', { org_id: 'hermes-labs', mode: 'merge' });

    expect(calls.map(call => call.url)).toEqual([
      'http://localhost:8780/v1/team-soul-backup-policy?org_id=hermes-labs',
      'http://localhost:8780/v1/team-soul-backup-policy',
      'http://localhost:8780/v1/backups/team-soul?org_id=hermes-labs',
      'http://localhost:8780/v1/backups/team-soul/run',
      'http://localhost:8780/v1/backups/team-soul/soul-backup-1/restore-preview',
      'http://localhost:8780/v1/backups/team-soul/soul-backup-1/restore-execute'
    ]);
  });

  it('manages team soul through the dedicated governance endpoints', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: 'http://localhost:8780',
      sessionToken: 'hcs_session_token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({
          org_id: 'hermes-labs',
          team_id: 'hermes-labs',
          content: '团队父人格：保持专业、透明、边界明确。',
          version: 2,
          checksum_sha256: 'sha256-team-soul',
          updated_at: '2026-05-24T10:00:00Z'
        }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.getTeamSoul('hermes-labs');
    await client.getRuntimeTeamSoul('hermes-labs');
    await client.updateTeamSoul('hermes-labs', {
      content: '团队父人格：先讲边界，再给行动。',
      updatedBy: 'hermes-labs:owner'
    });

    expect(calls.map(call => call.url)).toEqual([
      'http://localhost:8780/v1/team-soul?org_id=hermes-labs&team_id=hermes-labs',
      'http://localhost:8780/v1/runtime/team-soul?org_id=hermes-labs&team_id=hermes-labs',
      'http://localhost:8780/v1/team-soul'
    ]);
    expect(calls[2].init?.method).toBe('PUT');
    expect(calls[2].init?.headers).toMatchObject({
      Authorization: 'Bearer hcs_session_token'
    });
    expect(JSON.parse(String(calls[2].init?.body))).toEqual({
      org_id: 'hermes-labs',
      team_id: 'hermes-labs',
      content: '团队父人格：先讲边界，再给行动。',
      updated_by: 'hermes-labs:owner'
    });
  });
});
