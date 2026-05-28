export type JsonObject = Record<string, unknown>;

export type BootstrapForm = {
  teamName: string;
  adminEmail: string;
  adminDisplayName: string;
  adminUserId: string;
  adminPassword: string;
};

export type LoginForm = {
  orgId: string;
  userId: string;
  password: string;
};

export type MemberForm = {
  email: string;
  displayName: string;
  userId: string;
  role: string;
  password: string;
};

export type TeamMemoryForm = {
  content: string;
  memoryType: string;
  sensitivity: string;
};

export type TeamSoulForm = {
  content: string;
  teamId?: string;
  updatedBy?: string;
};

export type ClientOptions = {
  apiBase: string;
  sessionToken?: string;
  fetcher?: typeof fetch;
};

export function buildBootstrapPayload(form: BootstrapForm): JsonObject {
  const teamName = form.teamName.trim();
  return {
    org_slug: slugifyIdentifier(teamName),
    org_name: teamName,
    admin_email: form.adminEmail,
    admin_display_name: form.adminDisplayName,
    admin_user_id: form.adminUserId,
    admin_password: form.adminPassword
  };
}

function slugifyIdentifier(value: string) {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return slug || 'team';
}

export function createTeamCloudClient(options: ClientOptions) {
  const fetcher = options.fetcher ?? fetch;
  const base = options.apiBase.trim().replace(/\/+$/, '');
  const sessionToken = (options.sessionToken ?? '').trim();

  async function request<T>(path: string, init: RequestInit = {}, authMode: 'none' | 'session' = 'session'): Promise<T> {
    const token = authMode === 'session' ? sessionToken : '';
    const headers: Record<string, string> = {
      Accept: 'application/json',
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
    bootstrapStatus: () => request<JsonObject>('/v1/bootstrap/status', {}, 'none'),
    createSuperAdmin: (form: BootstrapForm) => request<JsonObject>('/v1/bootstrap/super-admin', {
      method: 'POST',
      body: JSON.stringify(buildBootstrapPayload(form))
    }, 'none'),
    login: (form: LoginForm) => request<JsonObject>('/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify({
        org_id: form.orgId,
        user_id: form.userId,
        password: form.password
      })
    }, 'none'),
    listOrganizations: () => request<{ items: JsonObject[] }>('/api/organizations'),
    createOrganization: (payload: JsonObject) => request<JsonObject>('/api/organizations', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    listMembers: (orgId: string) => request<{ items: JsonObject[] }>(`/api/organizations/${encodeURIComponent(orgId)}/members`),
    createMember: (orgId: string, form: MemberForm) => request<JsonObject>(`/api/organizations/${encodeURIComponent(orgId)}/members`, {
      method: 'POST',
      body: JSON.stringify({
        email: form.email,
        display_name: form.displayName,
        user_id: form.userId,
        role: form.role,
        password: form.password
      })
    }),
    updateMember: (orgId: string, memberId: string, payload: { email: string; displayName: string }) => request<JsonObject>(`/api/organizations/${encodeURIComponent(orgId)}/members/${encodeURIComponent(memberId)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        email: payload.email,
        display_name: payload.displayName
      })
    }),
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
    listTeamMemories: (orgId: string, status = '') => {
      const params = new URLSearchParams({
        org_id: orgId,
        scope: 'team_shared'
      });
      if (status) {
        params.set('status', status);
      }
      return request<{ items: JsonObject[] }>(`/v1/memory?${params.toString()}`);
    },
    createTeamMemory: (orgId: string, form: TeamMemoryForm) => request<JsonObject>('/v1/memory', {
      method: 'POST',
      body: JSON.stringify({
        org_id: orgId,
        scope: 'team_shared',
        status: 'active',
        source_type: 'admin_created',
        content: form.content,
        memory_type: form.memoryType,
        sensitivity: form.sensitivity
      })
    }),
    updateMemory: (memoryId: string, form: TeamMemoryForm) => request<JsonObject>(`/v1/memory/${encodeURIComponent(memoryId)}`, {
      method: 'PATCH',
      body: JSON.stringify({
        content: form.content,
        memory_type: form.memoryType,
        sensitivity: form.sensitivity
      })
    }),
    disableMemory: (memoryId: string) => request<JsonObject>(`/v1/memory/${encodeURIComponent(memoryId)}/disable`, {
      method: 'POST'
    }),
    deleteMemory: (memoryId: string) => request<JsonObject>(`/v1/memory/${encodeURIComponent(memoryId)}`, {
      method: 'DELETE'
    }),
    listReviews: (orgId: string) => request<{ items: JsonObject[] }>(`/v1/memory/review?org_id=${encodeURIComponent(orgId)}`),
    decideReview: (reviewId: string, action: 'approve' | 'reject', payload: JsonObject) => request<JsonObject>(`/v1/memory/review/${encodeURIComponent(reviewId)}/${action}`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    getTeamBackupPolicy: (orgId: string) => request<JsonObject>(`/v1/team-memory-backup-policy?org_id=${encodeURIComponent(orgId)}`),
    upsertTeamBackupPolicy: (payload: JsonObject) => request<JsonObject>('/v1/team-memory-backup-policy', {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
    getTeamSoulBackupPolicy: (orgId: string) => request<JsonObject>(`/v1/team-soul-backup-policy?org_id=${encodeURIComponent(orgId)}`),
    upsertTeamSoulBackupPolicy: (payload: JsonObject) => request<JsonObject>('/v1/team-soul-backup-policy', {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
    getTeamSoul: (orgId: string, teamId = orgId) => {
      const params = new URLSearchParams({
        org_id: orgId,
        team_id: teamId
      });
      return request<JsonObject>(`/v1/team-soul?${params.toString()}`);
    },
    getRuntimeTeamSoul: (orgId: string, teamId = orgId) => {
      const params = new URLSearchParams({
        org_id: orgId,
        team_id: teamId
      });
      return request<JsonObject>(`/v1/runtime/team-soul?${params.toString()}`);
    },
    updateTeamSoul: (orgId: string, form: TeamSoulForm) => request<JsonObject>('/v1/team-soul', {
      method: 'PUT',
      body: JSON.stringify({
        org_id: orgId,
        team_id: form.teamId?.trim() || orgId,
        content: form.content,
        ...(form.updatedBy?.trim() ? { updated_by: form.updatedBy.trim() } : {})
      })
    }),
    listTeamBackups: (orgId: string) => request<{ items: JsonObject[] }>(`/v1/backups/team?org_id=${encodeURIComponent(orgId)}`),
    runTeamBackup: (payload: JsonObject) => request<JsonObject>('/v1/backups/team/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    restoreTeamBackup: async (backupId: string, payload: JsonObject) => {
      await request<JsonObject>(`/v1/backups/team/${encodeURIComponent(backupId)}/restore-preview`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      return request<JsonObject>(`/v1/backups/team/${encodeURIComponent(backupId)}/restore-execute`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    },
    listTeamSoulBackups: (orgId: string) => request<{ items: JsonObject[] }>(`/v1/backups/team-soul?org_id=${encodeURIComponent(orgId)}`),
    runTeamSoulBackup: (payload: JsonObject) => request<JsonObject>('/v1/backups/team-soul/run', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
    restoreTeamSoulBackup: async (backupId: string, payload: JsonObject) => {
      await request<JsonObject>(`/v1/backups/team-soul/${encodeURIComponent(backupId)}/restore-preview`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      return request<JsonObject>(`/v1/backups/team-soul/${encodeURIComponent(backupId)}/restore-execute`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
    },
    auditEvents: (orgId: string, limit: number) => request<{ items: JsonObject[] }>(`/v1/audit/events?org_id=${encodeURIComponent(orgId)}&limit=${limit}`)
  };
}
