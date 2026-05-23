export type JsonObject = Record<string, unknown>;

export type BootstrapForm = {
  orgSlug: string;
  orgName: string;
  adminEmail: string;
  adminDisplayName: string;
  adminUserId: string;
};

export type ClientOptions = {
  apiBase: string;
  token: string;
  fetcher?: typeof fetch;
};

export function buildBootstrapPayload(form: BootstrapForm): JsonObject {
  return {
    org_slug: form.orgSlug,
    org_name: form.orgName,
    admin_email: form.adminEmail,
    admin_display_name: form.adminDisplayName,
    admin_user_id: form.adminUserId
  };
}

export function createTeamCloudClient(options: ClientOptions) {
  const fetcher = options.fetcher ?? fetch;
  const base = options.apiBase.trim().replace(/\/+$/, '');

  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.token.trim() ? { Authorization: `Bearer ${options.token.trim()}` } : {}),
      ...(init.headers as Record<string, string> | undefined)
    };
    const response = await fetcher(`${base}${path}`, { ...init, headers });
    const contentType = response.headers.get('Content-Type') ?? '';
    const payload = contentType.includes('application/json') ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof payload === 'object' && payload && 'detail' in payload ? String((payload as JsonObject).detail) : String(payload);
      throw new Error(detail || `request_failed_${response.status}`);
    }
    return payload as T;
  }

  return {
    bootstrapStatus: () => request<JsonObject>('/v1/bootstrap/status'),
    createSuperAdmin: (form: BootstrapForm) => request<JsonObject>('/v1/bootstrap/super-admin', {
      method: 'POST',
      body: JSON.stringify(buildBootstrapPayload(form))
    }),
    listOrganizations: () => request<{ items: JsonObject[] }>('/api/organizations'),
    createOrganization: (payload: JsonObject) => request<JsonObject>('/api/organizations', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    listTeams: (orgId: string) => request<{ items: JsonObject[] }>(`/api/organizations/${encodeURIComponent(orgId)}/teams`),
    createTeam: (orgId: string, payload: JsonObject) => request<JsonObject>(`/api/organizations/${encodeURIComponent(orgId)}/teams`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    listMembers: (orgId: string) => request<{ items: JsonObject[] }>(`/api/organizations/${encodeURIComponent(orgId)}/members`),
    inviteMember: (orgId: string, payload: JsonObject) => request<JsonObject>(`/api/organizations/${encodeURIComponent(orgId)}/members/invite`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    disableMember: (orgId: string, memberId: string) => request<JsonObject>(`/api/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(memberId)}/disable`, {
      method: 'PATCH'
    }),
    writeRelationship: (payload: JsonObject) => request<JsonObject>('/v1/authz/relationships', {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
    checkPermission: (payload: JsonObject) => request<JsonObject>('/v1/authz/check', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    listReviews: (orgId: string) => request<{ items: JsonObject[] }>(`/v1/memory/review?org_id=${encodeURIComponent(orgId)}`),
    decideReview: (reviewId: string, action: 'approve' | 'reject', payload: JsonObject) => request<JsonObject>(`/v1/memory/review/${encodeURIComponent(reviewId)}/${action}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    getBackupPolicy: (orgId: string, memberId: string) => request<JsonObject>(`/v1/me/memory-backup-policy?org_id=${encodeURIComponent(orgId)}&member_id=${encodeURIComponent(memberId)}`),
    upsertBackupPolicy: (payload: JsonObject) => request<JsonObject>('/v1/me/memory-backup-policy', {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
    runPersonalBackup: (payload: JsonObject) => request<JsonObject>('/v1/backups/personal/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    auditEvents: (orgId: string, limit: number) => request<{ items: JsonObject[] }>(`/v1/audit/events?org_id=${encodeURIComponent(orgId)}&limit=${limit}`)
  };
}
