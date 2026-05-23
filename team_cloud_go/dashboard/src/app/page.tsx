'use client';

import {
  Activity,
  ArchiveRestore,
  CheckCircle2,
  Database,
  KeyRound,
  Network,
  RefreshCw,
  Save,
  ShieldCheck,
  UsersRound
} from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { BootstrapForm, JsonObject, createTeamCloudClient } from '../lib/teamCloudClient';

type TabId = 'bootstrap' | 'organizations' | 'authz' | 'memory' | 'backup' | 'audit' | 'local';

type ActionState = {
  label: string;
  status: 'idle' | 'running' | 'ok' | 'error';
  detail: string;
};

const tabs: Array<{ id: TabId; label: string; icon: typeof ShieldCheck }> = [
  { id: 'bootstrap', label: '初始化', icon: ShieldCheck },
  { id: 'organizations', label: '组织', icon: UsersRound },
  { id: 'authz', label: '权限', icon: KeyRound },
  { id: 'memory', label: '记忆治理', icon: Database },
  { id: 'backup', label: '备份', icon: ArchiveRestore },
  { id: 'audit', label: '审计', icon: Activity },
  { id: 'local', label: '本地连接', icon: Network }
];

const emptyBootstrap: BootstrapForm = {
  orgSlug: 'hermes-labs',
  orgName: 'Hermes Labs',
  adminEmail: 'owner@example.com',
  adminDisplayName: 'Owner',
  adminUserId: 'owner'
};

function loadStored(key: string, fallback: string) {
  if (typeof window === 'undefined') {
    return fallback;
  }
  return window.sessionStorage.getItem(key) ?? fallback;
}

function storeValue(key: string, value: string) {
  if (typeof window !== 'undefined') {
    window.sessionStorage.setItem(key, value);
  }
}

function jsonSummary(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export default function TeamCloudDashboard() {
  const [apiBase, setApiBase] = useState('');
  const [token, setToken] = useState('');
  const [activeTab, setActiveTab] = useState<TabId>('bootstrap');
  const [status, setStatus] = useState<JsonObject | null>(null);
  const [action, setAction] = useState<ActionState>({ label: '待命', status: 'idle', detail: '' });
  const [bootstrap, setBootstrap] = useState<BootstrapForm>(emptyBootstrap);
  const [orgForm, setOrgForm] = useState({ slug: 'hermes-labs', name: 'Hermes Labs' });
  const [selectedOrg, setSelectedOrg] = useState('hermes-labs');
  const [teamForm, setTeamForm] = useState({ slug: 'platform', name: 'Platform' });
  const [memberForm, setMemberForm] = useState({ email: 'alice@example.com', displayName: 'Alice', userId: 'alice', role: 'member' });
  const [relationshipForm, setRelationshipForm] = useState({
    resourceType: 'team',
    resourceId: 'hermes-labs:platform',
    relation: 'member',
    subjectType: 'member',
    subjectId: 'hermes-labs:alice',
    permission: 'read_team'
  });
  const [reviewForm, setReviewForm] = useState({ orgId: 'hermes-labs', reviewId: '', actorMemberId: 'hermes-labs:owner', rejectReason: 'not approved for team memory' });
  const [backupForm, setBackupForm] = useState({ orgId: 'hermes-labs', memberId: 'hermes-labs:alice', cadence: 'daily', retentionCount: '7', enabled: true });
  const [auditForm, setAuditForm] = useState({ orgId: 'hermes-labs', limit: '50' });
  const [data, setData] = useState<JsonObject>({});

  useEffect(() => {
    setApiBase(loadStored('teamCloudDashboard.apiBase', ''));
    setToken(loadStored('teamCloudDashboard.token', ''));
  }, []);

  const client = useMemo(() => createTeamCloudClient({ apiBase, token }), [apiBase, token]);

  function updateApiBase(value: string) {
    setApiBase(value);
    storeValue('teamCloudDashboard.apiBase', value);
  }

  function updateToken(value: string) {
    setToken(value);
    storeValue('teamCloudDashboard.token', value);
  }

  async function run<T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) {
    setAction({ label, status: 'running', detail: '' });
    try {
      const result = await operation();
      onSuccess?.(result);
      setAction({ label, status: 'ok', detail: jsonSummary(result) });
    } catch (error) {
      setAction({ label, status: 'error', detail: error instanceof Error ? error.message : String(error) });
    }
  }

  function handleConnectionSubmit(event: FormEvent) {
    event.preventDefault();
    void run('读取服务状态', client.bootstrapStatus, result => setStatus(result));
  }

  function renderActivePanel() {
    switch (activeTab) {
      case 'bootstrap':
        return (
          <section className="panel" aria-labelledby="bootstrap-title">
            <PanelTitle id="bootstrap-title" icon={ShieldCheck} title="首次初始化" actionLabel="刷新状态" onAction={() => run('刷新状态', client.bootstrapStatus, result => setStatus(result))} />
            <StatusGrid status={status} />
            <form className="form-grid" onSubmit={event => {
              event.preventDefault();
              void run('创建超级管理员', () => client.createSuperAdmin(bootstrap), result => {
                setStatus(result as JsonObject);
                setSelectedOrg(bootstrap.orgSlug);
              });
            }}>
              <Field label="组织标识" value={bootstrap.orgSlug} onChange={value => setBootstrap({ ...bootstrap, orgSlug: value })} />
              <Field label="组织名称" value={bootstrap.orgName} onChange={value => setBootstrap({ ...bootstrap, orgName: value })} />
              <Field label="管理员邮箱" value={bootstrap.adminEmail} onChange={value => setBootstrap({ ...bootstrap, adminEmail: value })} />
              <Field label="管理员显示名" value={bootstrap.adminDisplayName} onChange={value => setBootstrap({ ...bootstrap, adminDisplayName: value })} />
              <Field label="管理员用户 ID" value={bootstrap.adminUserId} onChange={value => setBootstrap({ ...bootstrap, adminUserId: value })} />
              <button className="command primary" type="submit"><Save size={16} />创建超级管理员</button>
            </form>
          </section>
        );
      case 'organizations':
        return (
          <section className="panel" aria-labelledby="org-title">
            <PanelTitle id="org-title" icon={UsersRound} title="组织、团队和成员" actionLabel="加载组织" onAction={() => run('加载组织', client.listOrganizations, result => setData({ ...data, organizations: result.items }))} />
            <form className="form-grid" onSubmit={event => {
              event.preventDefault();
              void run('创建组织', () => client.createOrganization({ slug: orgForm.slug, name: orgForm.name }), result => {
                setSelectedOrg(String((result as JsonObject).id ?? orgForm.slug));
              });
            }}>
              <Field label="新组织标识" value={orgForm.slug} onChange={value => setOrgForm({ ...orgForm, slug: value })} />
              <Field label="新组织名称" value={orgForm.name} onChange={value => setOrgForm({ ...orgForm, name: value })} />
              <button className="command" type="submit"><Save size={16} />创建组织</button>
            </form>
            <div className="split">
              <form className="form-grid compact" onSubmit={event => {
                event.preventDefault();
                void run('创建团队', () => client.createTeam(selectedOrg, { slug: teamForm.slug, name: teamForm.name }), result => setData({ ...data, lastTeam: result }));
              }}>
                <Field label="选中组织 ID" value={selectedOrg} onChange={setSelectedOrg} />
                <Field label="团队标识" value={teamForm.slug} onChange={value => setTeamForm({ ...teamForm, slug: value })} />
                <Field label="团队名称" value={teamForm.name} onChange={value => setTeamForm({ ...teamForm, name: value })} />
                <button className="command" type="button" onClick={() => run('加载团队', () => client.listTeams(selectedOrg), result => setData({ ...data, teams: result.items }))}><RefreshCw size={16} />加载团队</button>
                <button className="command primary" type="submit"><Save size={16} />创建团队</button>
              </form>
              <form className="form-grid compact" onSubmit={event => {
                event.preventDefault();
                void run('邀请成员', () => client.inviteMember(selectedOrg, {
                  email: memberForm.email,
                  display_name: memberForm.displayName,
                  user_id: memberForm.userId,
                  role: memberForm.role
                }), result => setData({ ...data, lastMember: result }));
              }}>
                <Field label="成员邮箱" value={memberForm.email} onChange={value => setMemberForm({ ...memberForm, email: value })} />
                <Field label="成员显示名" value={memberForm.displayName} onChange={value => setMemberForm({ ...memberForm, displayName: value })} />
                <Field label="成员用户 ID" value={memberForm.userId} onChange={value => setMemberForm({ ...memberForm, userId: value })} />
                <SelectField label="成员角色" value={memberForm.role} options={['owner', 'admin', 'member', 'viewer']} onChange={value => setMemberForm({ ...memberForm, role: value })} />
                <button className="command" type="button" onClick={() => run('加载成员', () => client.listMembers(selectedOrg), result => setData({ ...data, members: result.items }))}><RefreshCw size={16} />加载成员</button>
                <button className="command primary" type="submit"><Save size={16} />邀请成员</button>
              </form>
            </div>
          </section>
        );
      case 'authz':
        return (
          <section className="panel" aria-labelledby="authz-title">
            <PanelTitle id="authz-title" icon={KeyRound} title="权限关系" />
            <form className="form-grid" onSubmit={event => {
              event.preventDefault();
              void run('写入权限关系', () => client.writeRelationship({
                org_id: selectedOrg,
                resource_type: relationshipForm.resourceType,
                resource_id: relationshipForm.resourceId,
                relation: relationshipForm.relation,
                subject_type: relationshipForm.subjectType,
                subject_id: relationshipForm.subjectId,
                idempotency_key: `${selectedOrg}:${relationshipForm.resourceType}:${relationshipForm.resourceId}:${relationshipForm.relation}:${relationshipForm.subjectId}`
              }));
            }}>
              <Field label="权限组织 ID" value={selectedOrg} onChange={setSelectedOrg} />
              <Field label="资源类型" value={relationshipForm.resourceType} onChange={value => setRelationshipForm({ ...relationshipForm, resourceType: value })} />
              <Field label="资源 ID" value={relationshipForm.resourceId} onChange={value => setRelationshipForm({ ...relationshipForm, resourceId: value })} />
              <Field label="关系" value={relationshipForm.relation} onChange={value => setRelationshipForm({ ...relationshipForm, relation: value })} />
              <Field label="主体类型" value={relationshipForm.subjectType} onChange={value => setRelationshipForm({ ...relationshipForm, subjectType: value })} />
              <Field label="主体 ID" value={relationshipForm.subjectId} onChange={value => setRelationshipForm({ ...relationshipForm, subjectId: value })} />
              <Field label="检查权限" value={relationshipForm.permission} onChange={value => setRelationshipForm({ ...relationshipForm, permission: value })} />
              <button className="command" type="button" onClick={() => run('检查权限', () => client.checkPermission({
                org_id: selectedOrg,
                resource_type: relationshipForm.resourceType,
                resource_id: relationshipForm.resourceId,
                permission: relationshipForm.permission,
                subject_type: relationshipForm.subjectType,
                subject_id: relationshipForm.subjectId
              }))}><ShieldCheck size={16} />检查权限</button>
              <button className="command primary" type="submit"><Save size={16} />写入关系</button>
            </form>
          </section>
        );
      case 'memory':
        return (
          <section className="panel" aria-labelledby="memory-title">
            <PanelTitle id="memory-title" icon={Database} title="记忆治理" actionLabel="加载待审" onAction={() => run('加载待审记忆', () => client.listReviews(reviewForm.orgId), result => setData({ ...data, reviews: result.items }))} />
            <form className="form-grid" onSubmit={event => event.preventDefault()}>
              <Field label="记忆组织 ID" value={reviewForm.orgId} onChange={value => setReviewForm({ ...reviewForm, orgId: value })} />
              <Field label="Review ID" value={reviewForm.reviewId} onChange={value => setReviewForm({ ...reviewForm, reviewId: value })} />
              <Field label="审核成员 ID" value={reviewForm.actorMemberId} onChange={value => setReviewForm({ ...reviewForm, actorMemberId: value })} />
              <Field label="拒绝理由" value={reviewForm.rejectReason} onChange={value => setReviewForm({ ...reviewForm, rejectReason: value })} />
              <button className="command primary" type="button" onClick={() => run('批准记忆', () => client.decideReview(reviewForm.reviewId, 'approve', { actor_member_id: reviewForm.actorMemberId }))}><CheckCircle2 size={16} />批准</button>
              <button className="command danger" type="button" onClick={() => run('拒绝记忆', () => client.decideReview(reviewForm.reviewId, 'reject', { actor_member_id: reviewForm.actorMemberId, reason: reviewForm.rejectReason }))}>拒绝</button>
            </form>
          </section>
        );
      case 'backup':
        return (
          <section className="panel" aria-labelledby="backup-title">
            <PanelTitle id="backup-title" icon={ArchiveRestore} title="个人记忆备份" />
            <form className="form-grid" onSubmit={event => {
              event.preventDefault();
              void run('保存备份策略', () => client.upsertBackupPolicy({
                org_id: backupForm.orgId,
                member_id: backupForm.memberId,
                cadence: backupForm.cadence,
                enabled: backupForm.enabled,
                retention_count: Number(backupForm.retentionCount)
              }));
            }}>
              <Field label="备份组织 ID" value={backupForm.orgId} onChange={value => setBackupForm({ ...backupForm, orgId: value })} />
              <Field label="备份成员 ID" value={backupForm.memberId} onChange={value => setBackupForm({ ...backupForm, memberId: value })} />
              <SelectField label="备份周期" value={backupForm.cadence} options={['hourly', 'daily', 'weekly', 'monthly']} onChange={value => setBackupForm({ ...backupForm, cadence: value })} />
              <Field label="保留份数" value={backupForm.retentionCount} onChange={value => setBackupForm({ ...backupForm, retentionCount: value })} type="number" />
              <label className="toggle"><input type="checkbox" checked={backupForm.enabled} onChange={event => setBackupForm({ ...backupForm, enabled: event.target.checked })} />启用策略</label>
              <button className="command" type="button" onClick={() => run('读取备份策略', () => client.getBackupPolicy(backupForm.orgId, backupForm.memberId))}><RefreshCw size={16} />读取策略</button>
              <button className="command" type="button" onClick={() => run('立即备份', () => client.runPersonalBackup({ org_id: backupForm.orgId, member_id: backupForm.memberId }))}><ArchiveRestore size={16} />立即备份</button>
              <button className="command primary" type="submit"><Save size={16} />保存策略</button>
            </form>
          </section>
        );
      case 'audit':
        return (
          <section className="panel" aria-labelledby="audit-title">
            <PanelTitle id="audit-title" icon={Activity} title="审计事件" actionLabel="加载审计" onAction={() => run('加载审计', () => client.auditEvents(auditForm.orgId, Number(auditForm.limit)), result => setData({ ...data, audit: result.items }))} />
            <div className="form-grid">
              <Field label="审计组织 ID" value={auditForm.orgId} onChange={value => setAuditForm({ ...auditForm, orgId: value })} />
              <Field label="审计条数" value={auditForm.limit} onChange={value => setAuditForm({ ...auditForm, limit: value })} type="number" />
            </div>
          </section>
        );
      case 'local':
        return (
          <section className="panel" aria-labelledby="local-title">
            <PanelTitle id="local-title" icon={Network} title="Hermes 本地连接" />
            <div className="connection-grid">
              <OutputBlock title="Team Cloud URL" value={apiBase || 'http://localhost:8780'} />
              <OutputBlock title="Dashboard URL" value={`${apiBase || 'http://localhost:8780'}/dashboard/`} />
              <OutputBlock title="Token scope" value={token ? 'service-token/session token present' : 'token empty'} />
            </div>
          </section>
        );
    }
  }

  return (
    <main className="app-shell">
      <aside className="sidebar" aria-label="Team Cloud Admin navigation">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <h1>Team Cloud Admin</h1>
            <span>Go service dashboard</span>
          </div>
        </div>
        <nav className="nav-list">
          {tabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button key={tab.id} className={tab.id === activeTab ? 'nav-item active' : 'nav-item'} type="button" onClick={() => setActiveTab(tab.id)}>
                <Icon size={17} />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </aside>
      <section className="workspace">
        <form className="topbar" onSubmit={handleConnectionSubmit}>
          <Field label="API 地址" value={apiBase} onChange={updateApiBase} placeholder="留空使用同源 /v1 和 /api" />
          <Field label="Service token" value={token} onChange={updateToken} type="password" placeholder="Bearer token" />
          <button className="command primary" type="submit"><RefreshCw size={16} />检查服务</button>
        </form>
        {renderActivePanel()}
        <section className={`result result-${action.status}`} aria-live="polite">
          <div>
            <strong>{action.label}</strong>
            <span>{action.status}</span>
          </div>
          <pre>{action.detail || jsonSummary({ status, data })}</pre>
        </section>
      </section>
    </main>
  );
}

function PanelTitle({ id, icon: Icon, title, actionLabel, onAction }: { id: string; icon: typeof ShieldCheck; title: string; actionLabel?: string; onAction?: () => void }) {
  return (
    <div className="panel-title">
      <div>
        <Icon size={20} />
        <h2 id={id}>{title}</h2>
      </div>
      {actionLabel && onAction ? <button className="command" type="button" onClick={onAction}><RefreshCw size={16} />{actionLabel}</button> : null}
    </div>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder }: { label: string; value: string; onChange: (value: string) => void; type?: string; placeholder?: string }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type={type} value={value} placeholder={placeholder} onChange={event => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value} onChange={event => onChange(event.target.value)}>
        {options.map(option => <option key={option} value={option}>{option}</option>)}
      </select>
    </label>
  );
}

function OutputBlock({ title, value }: { title: string; value: string }) {
  return (
    <div className="output-block">
      <span>{title}</span>
      <code>{value}</code>
    </div>
  );
}

function StatusGrid({ status }: { status: JsonObject | null }) {
  const checks = (status?.checks ?? {}) as JsonObject;
  return (
    <div className="status-grid">
      <Metric label="初始化" value={status?.initialized === true ? 'yes' : 'no'} />
      <Metric label="组织数" value={String(status?.organization_count ?? 0)} />
      <Metric label="Owner 数" value={String(status?.owner_count ?? 0)} />
      <Metric label="后端" value={checks.backend === false ? 'down' : 'ready'} />
      <Metric label="授权" value={checks.authz === false ? 'down' : 'ready'} />
      <Metric label="Dashboard" value={checks.dashboard === false ? 'off' : 'ready'} />
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
