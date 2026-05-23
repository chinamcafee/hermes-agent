import { buildBootstrapPayload, createTeamCloudClient } from './teamCloudClient';

describe('teamCloudClient', () => {
  it('builds the bootstrap payload expected by the Go service', () => {
    expect(buildBootstrapPayload({
      orgSlug: 'hermes-labs',
      orgName: 'Hermes Labs',
      adminEmail: 'owner@example.com',
      adminDisplayName: 'Owner Example',
      adminUserId: 'owner'
    })).toEqual({
      org_slug: 'hermes-labs',
      org_name: 'Hermes Labs',
      admin_email: 'owner@example.com',
      admin_display_name: 'Owner Example',
      admin_user_id: 'owner'
    });
  });

  it('uses relative URLs and bearer auth for service calls', async () => {
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    const client = createTeamCloudClient({
      apiBase: '',
      token: 'dev-token',
      fetcher: async (url, init) => {
        calls.push({ url: String(url), init });
        return new Response(JSON.stringify({ initialized: false }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    });

    await client.bootstrapStatus();

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe('/v1/bootstrap/status');
    expect(calls[0].init?.headers).toMatchObject({
      Authorization: 'Bearer dev-token'
    });
  });
});
