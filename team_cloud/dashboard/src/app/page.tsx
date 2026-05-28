'use client';

import {
  Activity,
  ArchiveRestore,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Clipboard,
  Database,
  KeyRound,
  LayoutDashboard,
  LockKeyhole,
  Network,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  UserPlus,
  UsersRound,
  X
} from 'lucide-react';
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from 'react';
import { BootstrapForm, JsonObject, MemberForm, TeamMemoryForm, TeamSoulForm, createTeamCloudClient } from '../lib/teamCloudClient';

type AdminView = 'overview' | 'members' | 'permissions' | 'memory' | 'soul' | 'backup' | 'audit' | 'local';

type ActionState = {
  label: string;
  status: 'idle' | 'running' | 'ok' | 'error';
  detail: string;
};

type StoredMember = {
  id: string;
  org_id: string;
  user_id?: string;
  role: string;
  status?: string;
  display_name?: string;
  email?: string;
};

type MemoryDialog = 'create' | 'edit' | 'review' | null;

const adminViews: Array<{ id: AdminView; label: string; icon: typeof ShieldCheck }> = [
  { id: 'overview', label: '概览', icon: LayoutDashboard },
  { id: 'members', label: '团队成员', icon: UsersRound },
  { id: 'permissions', label: '权限中心', icon: KeyRound },
  { id: 'memory', label: '记忆治理', icon: Database },
  { id: 'soul', label: '团队父人格中心', icon: Sparkles },
  { id: 'backup', label: '备份管理', icon: ArchiveRestore },
  { id: 'audit', label: '审计时间线', icon: Activity },
  { id: 'local', label: '本地连接', icon: Network }
];

const emptyBootstrap: BootstrapForm = {
  teamName: 'Hermes Labs',
  adminEmail: 'owner@example.com',
  adminDisplayName: 'Owner',
  adminUserId: 'owner',
  adminPassword: ''
};

const emptyMember: MemberForm = {
  email: '',
  displayName: '',
  userId: '',
  role: 'user',
  password: ''
};

const emptyTeamMemory: TeamMemoryForm = {
  content: '',
  memoryType: 'fact',
  sensitivity: 'normal'
};

const emptyTeamSoul: TeamSoulForm = {
  content: ''
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

function loadMember(): StoredMember | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.sessionStorage.getItem('teamCloudDashboard.member');
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as StoredMember;
  } catch {
    return null;
  }
}

function jsonSummary(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export default function TeamCloudDashboard() {
  const [apiBase, setApiBase] = useState('');
  const [sessionToken, setSessionToken] = useState('');
  const [member, setMember] = useState<StoredMember | null>(null);
  const [status, setStatus] = useState<JsonObject | null>(null);
  const [activeView, setActiveView] = useState<AdminView>('overview');
  const [action, setAction] = useState<ActionState>({ label: '待命', status: 'idle', detail: '' });

  useEffect(() => {
    setApiBase(loadStored('teamCloudDashboard.apiBase', ''));
    setSessionToken(loadStored('teamCloudDashboard.sessionToken', ''));
    setMember(loadMember());
  }, []);

  const client = useMemo(() => createTeamCloudClient({ apiBase, sessionToken }), [apiBase, sessionToken]);

  async function run<T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) {
    setAction({ label, status: 'running', detail: '' });
    try {
      const result = await operation();
      onSuccess?.(result);
      setAction({ label, status: 'ok', detail: jsonSummary(result) });
      return result;
    } catch (error) {
      setAction({ label, status: 'error', detail: error instanceof Error ? error.message : String(error) });
      throw error;
    }
  }

  async function refreshStatus() {
    try {
      const next = await client.bootstrapStatus();
      setStatus(next);
    } catch (error) {
      setAction({ label: '读取服务状态', status: 'error', detail: error instanceof Error ? error.message : String(error) });
    }
  }

  useEffect(() => {
    void refreshStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiBase]);

  function updateApiBase(value: string) {
    setApiBase(value);
    storeValue('teamCloudDashboard.apiBase', value);
  }

  function handleSession(token: string, nextMember: StoredMember) {
    setSessionToken(token);
    setMember(nextMember);
    storeValue('teamCloudDashboard.sessionToken', token);
    storeValue('teamCloudDashboard.member', JSON.stringify(nextMember));
  }

  function clearSession() {
    setSessionToken('');
    setMember(null);
    storeValue('teamCloudDashboard.sessionToken', '');
    storeValue('teamCloudDashboard.member', '');
  }

  const initialized = status?.initialized === true;
  if (!initialized) {
    return <BootstrapLanding apiBase={apiBase} status={status} action={action} client={client} run={run} refreshStatus={refreshStatus} updateApiBase={updateApiBase} />;
  }
  if (!sessionToken || !member) {
    return <LoginPage apiBase={apiBase} status={status} action={action} client={client} run={run} updateApiBase={updateApiBase} onLogin={handleSession} />;
  }
  return <AdminShell apiBase={apiBase} status={status} action={action} client={client} member={member} activeView={activeView} setActiveView={setActiveView} refreshStatus={refreshStatus} run={run} clearSession={clearSession} />;
}

function BootstrapLanding({ apiBase, status, action, client, run, refreshStatus, updateApiBase }: {
  apiBase: string;
  status: JsonObject | null;
  action: ActionState;
  client: ReturnType<typeof createTeamCloudClient>;
  run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined>;
  refreshStatus: () => Promise<void>;
  updateApiBase: (value: string) => void;
}) {
  const [bootstrap, setBootstrap] = useState<BootstrapForm>(emptyBootstrap);
  const [step, setStep] = useState(0);
  const checks = (status?.checks ?? {}) as JsonObject;
  const steps = [
    {
      label: '团队',
      title: '创建团队空间',
      body: (
        <div className="form-grid one">
          <Field label="团队名称" value={bootstrap.teamName} onChange={value => setBootstrap({ ...bootstrap, teamName: value })} />
        </div>
      )
    },
    {
      label: '超级管理员',
      title: '创建管理页用户',
      body: (
        <div className="form-grid two">
          <Field label="超级管理员邮箱" value={bootstrap.adminEmail} onChange={value => setBootstrap({ ...bootstrap, adminEmail: value })} />
          <Field label="超级管理员显示名" value={bootstrap.adminDisplayName} onChange={value => setBootstrap({ ...bootstrap, adminDisplayName: value })} />
          <Field label="超级管理员帐号" value={bootstrap.adminUserId} onChange={value => setBootstrap({ ...bootstrap, adminUserId: value })} />
          <Field label="超级管理员密码" value={bootstrap.adminPassword} onChange={value => setBootstrap({ ...bootstrap, adminPassword: value })} type="password" />
        </div>
      )
    },
    {
      label: '确认',
      title: '确认初始化信息',
      body: (
        <div className="review-grid">
          <SummaryCard title="团队" rows={[['名称', bootstrap.teamName]]} />
          <SummaryCard title="超级管理员" rows={[['帐号', bootstrap.adminUserId], ['邮箱', bootstrap.adminEmail]]} />
        </div>
      )
    }
  ];
  const canSubmit = step === steps.length - 1;
  return (
    <main className="setup-shell">
      <section className="setup-hero">
        <div>
          <div className="hero-mark"><Sparkles size={22} /></div>
          <div>
            <span className="eyebrow">Vega Dark Setup</span>
            <h1>Team Cloud 初始化引导</h1>
          </div>
        </div>
        <button className="command" type="button" onClick={refreshStatus}><RefreshCw size={16} />检查服务</button>
      </section>
      <section className="setup-status surface">
        <SetupCheck title="PostgreSQL" ok={checks.postgres_configured === true && checks.postgres_backend_active !== false} detail={checks.postgres_backend_active === false ? 'restart required' : checks.backend === false ? 'not ready' : 'env ready'} />
        <SetupCheck title="Redis Session" ok={checks.session_store === true} detail={checks.redis_configured === true ? 'redis' : 'local memory'} />
        <SetupCheck title="对象存储" ok={true} detail={checks.minio_configured === true ? 'backup enabled' : 'optional'} />
        <Field label="API 地址" value={apiBase} onChange={updateApiBase} placeholder="留空使用同源 /v1 和 /api" />
      </section>
      <form className="wizard-shell surface" onSubmit={event => {
          event.preventDefault();
          if (canSubmit) {
            void run('创建团队和超级管理员', () => client.createSuperAdmin(bootstrap), result => {
              const organization = ((result as JsonObject).organization ?? {}) as JsonObject;
              const orgID = String(organization.id ?? '');
              if (orgID) {
                storeValue('teamCloudDashboard.orgId', orgID);
              }
              void refreshStatus();
            });
          }
        }}>
        <div className="wizard-progress">
          {steps.map((item, index) => (
            <button key={item.label} type="button" className={index === step ? 'step-pill active' : index < step ? 'step-pill done' : 'step-pill'} onClick={() => setStep(index)}>
              <span>{index + 1}</span>{item.label}
            </button>
          ))}
        </div>
        <div className="wizard-page">
          <span className="eyebrow">步骤 {step + 1} / {steps.length}</span>
          <h2>{steps[step].title}</h2>
          {steps[step].body}
        </div>
        <div className="wizard-actions">
          <button className="command" type="button" disabled={step === 0} onClick={() => setStep(Math.max(0, step - 1))}><ArrowLeft size={16} />上一步</button>
          {canSubmit ? (
            <button className="command primary" type="submit"><ShieldCheck size={16} />完成初始化</button>
          ) : (
            <button className="command primary" type="button" onClick={() => setStep(Math.min(steps.length - 1, step + 1))}>下一步<ArrowRight size={16} /></button>
          )}
        </div>
      </form>
      <section className="setup-grid">
        <SetupCheck title="团队" ok={Number(status?.organization_count ?? 0) === 1} detail={`${status?.organization_count ?? 0}`} />
        <SetupCheck title="超级管理员" ok={Number(status?.super_admin_count ?? 0) === 1} detail={`${status?.super_admin_count ?? 0}`} />
        <div className="setup-note">
          <strong>连接配置由 Kubernetes Secret / env 注入</strong>
          <span>初始化向导只创建业务团队和第一个超级管理员帐号。</span>
        </div>
      </section>
      <ResultStrip action={action} fallback={{ status }} />
    </main>
  );
}

function SummaryCard({ title, rows }: { title: string; rows: string[][] }) {
  return (
    <div className="summary-card">
      <strong>{title}</strong>
      <div>
        {rows.map(([label, value]) => (
          <p key={label}><span>{label}</span><code>{value || '-'}</code></p>
        ))}
      </div>
    </div>
  );
}

function LoginPage({ apiBase, status, action, client, run, updateApiBase, onLogin }: {
  apiBase: string;
  status: JsonObject | null;
  action: ActionState;
  client: ReturnType<typeof createTeamCloudClient>;
  run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined>;
  updateApiBase: (value: string) => void;
  onLogin: (token: string, member: StoredMember) => void;
}) {
  const [form, setForm] = useState(() => ({ orgId: loadStored('teamCloudDashboard.orgId', 'hermes-labs'), userId: 'owner', password: '' }));
  return (
    <main className="login-shell">
      <form className="surface login-panel" onSubmit={event => {
        event.preventDefault();
        void run('管理台登录', () => client.login(form), result => {
          const token = String((result as JsonObject).token ?? '');
          const nextMember = ((result as JsonObject).member ?? {}) as StoredMember;
          onLogin(token, nextMember);
        });
      }}>
        <div className="login-mark"><LockKeyhole size={30} /></div>
        <h1>管理台登录</h1>
        <div className="form-stack">
          <Field label="API 地址" value={apiBase} onChange={updateApiBase} />
          <Field label="团队标识" value={form.orgId} onChange={value => setForm({ ...form, orgId: value })} />
          <Field label="帐号" value={form.userId} onChange={value => setForm({ ...form, userId: value })} />
          <Field label="密码" value={form.password} onChange={value => setForm({ ...form, password: value })} type="password" />
        </div>
        <button className="command primary wide" type="submit"><ShieldCheck size={16} />登录</button>
        <ResultStrip action={action} fallback={{ status }} compact />
      </form>
    </main>
  );
}

function AdminShell({ apiBase, status, action, client, member, activeView, setActiveView, refreshStatus, run, clearSession }: {
  apiBase: string;
  status: JsonObject | null;
  action: ActionState;
  client: ReturnType<typeof createTeamCloudClient>;
  member: StoredMember;
  activeView: AdminView;
  setActiveView: (view: AdminView) => void;
  refreshStatus: () => Promise<void>;
  run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined>;
  clearSession: () => void;
}) {
  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="brand">
          <ShieldCheck size={28} />
          <div>
            <h1>Team Cloud Admin</h1>
            <span>{member.role}</span>
          </div>
        </div>
        <nav className="nav-list" aria-label="Team Cloud 管理导航">
          {adminViews.map(view => {
            const Icon = view.icon;
            return <button key={view.id} className={activeView === view.id ? 'nav-item active' : 'nav-item'} type="button" onClick={() => setActiveView(view.id)}><Icon size={17} />{view.label}</button>;
          })}
        </nav>
      </aside>
      <section className="admin-workspace">
        <header className="admin-topbar">
          <div>
            <strong>{member.display_name || member.id}</strong>
            <span>{member.org_id}</span>
          </div>
          <div className="topbar-actions">
            <button className="command" type="button" onClick={refreshStatus}><RefreshCw size={16} />刷新状态</button>
            <button className="command" type="button" onClick={clearSession}>退出</button>
          </div>
        </header>
        {activeView === 'overview' ? <OverviewView status={status} /> : null}
        {activeView === 'members' ? <MembersView orgId={member.org_id} currentRole={member.role} client={client} run={run} /> : null}
        {activeView === 'permissions' ? <PermissionsView orgId={member.org_id} client={client} run={run} /> : null}
        {activeView === 'memory' ? <MemoryView orgId={member.org_id} client={client} run={run} /> : null}
        {activeView === 'soul' ? <TeamSoulView orgId={member.org_id} memberId={member.id} client={client} run={run} /> : null}
        {activeView === 'backup' ? <BackupView orgId={member.org_id} client={client} run={run} /> : null}
        {activeView === 'audit' ? <AuditView orgId={member.org_id} client={client} run={run} /> : null}
        {activeView === 'local' ? <LocalConnectionView apiBase={apiBase} member={member} /> : null}
        <ResultStrip action={action} fallback={{ status }} />
      </section>
    </main>
  );
}

function OverviewView({ status }: { status: JsonObject | null }) {
  const checks = (status?.checks ?? {}) as JsonObject;
  return (
    <section className="view-stack">
      <div className="view-heading">
        <h2>团队运营概览</h2>
        <span>{status?.status === 'ready' ? 'ready' : 'attention'}</span>
      </div>
      <div className="kpi-grid">
        <Metric label="团队空间" value={String(status?.organization_count ?? 0)} />
        <Metric label="超级管理员" value={String(status?.super_admin_count ?? 0)} />
        <Metric label="PostgreSQL" value={checks.postgres_configured === true ? 'ready' : 'missing'} />
        <Metric label="对象存储" value={checks.minio_configured === true ? 'backup enabled' : 'optional'} />
      </div>
      <div className="operations-grid">
        <StatusPanel title="服务健康" rows={[['Backend', checks.backend], ['Authz', checks.authz], ['Dashboard', checks.dashboard]]} />
        <StatusPanel title="数据面" rows={[['PostgreSQL', checks.postgres_configured], ['Object Store optional', true], ['Team Memory Backup', checks.backup_object_store !== false]]} />
      </div>
      <div className="surface boundary-note">
        <Sparkles size={17} />
        <span>团队父人格配置中心已内置在管理台，可在左侧“团队父人格中心”中编辑父人格、查看运行时读取结果，并在备份管理中执行团队父人格备份与恢复。</span>
      </div>
    </section>
  );
}

function MembersView({ orgId, currentRole, client, run }: {
  orgId: string;
  currentRole: string;
  client: ReturnType<typeof createTeamCloudClient>;
  run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined>;
}) {
  const [items, setItems] = useState<JsonObject[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<JsonObject | null>(null);
  const [query, setQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [form, setForm] = useState<MemberForm>(emptyMember);
  const canCreateAdmin = currentRole === 'super_admin';
  const visibleItems = items.filter(item => {
    const haystack = `${item.user_id ?? ''} ${item.email ?? ''} ${item.display_name ?? ''}`.toLowerCase();
    const role = String(item.role ?? '');
    return haystack.includes(query.trim().toLowerCase()) && (roleFilter === 'all' || role === roleFilter);
  });
  const loadMembers = () => run('加载成员', () => client.listMembers(orgId), result => setItems(result.items));
  const replaceMember = (member: JsonObject) => setItems(items.map(item => item.id === member.id ? member : item));
  return (
    <section className="view-stack">
      <div className="view-heading">
        <h2>团队成员</h2>
        <div className="toolbar">
          <button className="command" type="button" onClick={() => void loadMembers()}><RefreshCw size={16} />刷新成员</button>
          <button className="command primary" type="button" onClick={() => setShowCreate(true)}><UserPlus size={16} />新建成员</button>
        </div>
      </div>
      <div className="surface filter-bar">
        <Field label="查询成员" value={query} onChange={setQuery} placeholder="帐号、邮箱或显示名" />
        <SelectField label="角色筛选" value={roleFilter} options={['all', 'super_admin', 'admin', 'user']} onChange={setRoleFilter} />
        <div className="filter-meta"><SlidersHorizontal size={16} />{visibleItems.length} / {items.length}</div>
      </div>
      <MembersTable
        items={visibleItems}
        onEdit={item => setEditing(item)}
        onDisable={item => void run('停用成员', () => client.disableMember(orgId, String(item.id ?? '')), result => replaceMember(result as JsonObject))}
      />
      {showCreate ? (
        <form className="drawer-form" onSubmit={event => {
          event.preventDefault();
          void run('创建成员', () => client.createMember(orgId, form), result => {
            setItems([...items, result as JsonObject]);
            setShowCreate(false);
            setForm(emptyMember);
          });
        }}>
          <SectionTitle icon={Plus} title="新建成员帐号" />
          <div className="form-grid two">
            <Field label="邮箱" value={form.email} onChange={value => setForm({ ...form, email: value })} />
            <Field label="显示名" value={form.displayName} onChange={value => setForm({ ...form, displayName: value })} />
            <Field label="帐号" value={form.userId} onChange={value => setForm({ ...form, userId: value })} />
            <SelectField label="角色" value={form.role} options={canCreateAdmin ? ['admin', 'user'] : ['user']} onChange={value => setForm({ ...form, role: value })} />
            <Field label="初始密码" value={form.password} onChange={value => setForm({ ...form, password: value })} type="password" />
          </div>
          <button className="command primary" type="submit"><Save size={16} />创建帐号</button>
        </form>
      ) : null}
      {editing ? (
        <form className="drawer-form" onSubmit={event => {
          event.preventDefault();
          void run('编辑成员', () => client.updateMember(orgId, String(editing.id ?? ''), {
            email: String(editing.email ?? ''),
            displayName: String(editing.display_name ?? '')
          }), result => {
            replaceMember(result as JsonObject);
            setEditing(null);
          });
        }}>
          <SectionTitle icon={Pencil} title="编辑成员资料" />
          <div className="form-grid two">
            <Field label="邮箱" value={String(editing.email ?? '')} onChange={value => setEditing({ ...editing, email: value })} />
            <Field label="显示名" value={String(editing.display_name ?? '')} onChange={value => setEditing({ ...editing, display_name: value })} />
            <Field label="帐号" value={String(editing.user_id ?? '')} onChange={() => undefined} readOnly />
            <Field label="角色" value={String(editing.role ?? '')} onChange={() => undefined} readOnly />
          </div>
          <div className="toolbar">
            <button className="command" type="button" onClick={() => setEditing(null)}>取消</button>
            <button className="command primary" type="submit"><Save size={16} />保存编辑</button>
          </div>
        </form>
      ) : null}
    </section>
  );
}

function PermissionsView({ orgId }: { orgId: string; client: ReturnType<typeof createTeamCloudClient>; run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined> }) {
  const matrix = [
    ['super_admin', '唯一超级管理员；可创建管理员和用户，管理团队记忆、团队备份、审计和成员生命周期。'],
    ['admin', '可创建和管理普通用户，治理团队记忆，执行团队记忆备份和恢复。'],
    ['user', '可登录 Hermes CLI，读取团队记忆，提交自动抽取候选，不可进入管理设置。']
  ];
  return (
    <section className="view-stack">
      <div className="view-heading"><h2>权限中心</h2><span>server-enforced roles</span></div>
      <div className="permissions-layout">
        <div className="role-matrix expanded">
          {matrix.map(([role, detail]) => <div key={role}><strong>{role}</strong><span>{detail}</span></div>)}
        </div>
        <section className="surface policy-card">
          <SectionTitle icon={KeyRound} title="固定权限模型" />
          <DataTable
            columns={['资源', 'super_admin', 'admin', 'user']}
            rows={[
              ['成员管理', '全部', '普通用户', '无'],
              ['团队记忆治理', '全部', '全部', '读取和提交候选'],
              ['团队备份管理', '全部', '执行和恢复', '无'],
              ['审计时间线', '读取', '读取', '无']
            ]}
            empty="暂无权限模型"
          />
          <OutputBlock title="当前团队" value={orgId} />
        </section>
      </div>
    </section>
  );
}

function MemoryView({ orgId, client, run }: { orgId: string; client: ReturnType<typeof createTeamCloudClient>; run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined> }) {
  const [reviews, setReviews] = useState<JsonObject[]>([]);
  const [memories, setMemories] = useState<JsonObject[]>([]);
  const [statusFilter, setStatusFilter] = useState('active');
  const [selected, setSelected] = useState('');
  const [selectedReview, setSelectedReview] = useState('');
  const [reason, setReason] = useState('');
  const [createForm, setCreateForm] = useState<TeamMemoryForm>(emptyTeamMemory);
  const [editForm, setEditForm] = useState<TeamMemoryForm>(emptyTeamMemory);
  const [dialog, setDialog] = useState<MemoryDialog>(null);
  const selectedMemory = memories.find(item => String(item.id ?? '') === selected);

  function refreshMemories() {
    return run('加载团队记忆', () => client.listTeamMemories(orgId, statusFilter), result => {
      setMemories(result.items);
      if (selected && !result.items.some(item => String(item.id ?? '') === selected)) {
        setSelected('');
        setEditForm(emptyTeamMemory);
      }
    });
  }

  function refreshReviews() {
    return run('加载待审记忆', () => client.listReviews(orgId), result => setReviews(result.items));
  }

  useEffect(() => {
    void refreshMemories();
    void refreshReviews();
  }, [orgId, statusFilter]);

  function selectMemory(item: JsonObject) {
    setSelected(String(item.id ?? ''));
    setEditForm({
      content: String(item.content ?? ''),
      memoryType: String(item.memory_type ?? 'fact'),
      sensitivity: String(item.sensitivity ?? 'normal')
    });
  }

  function openCreateDialog() {
    setCreateForm(emptyTeamMemory);
    setDialog('create');
  }

  function openEditDialog(item: JsonObject) {
    selectMemory(item);
    setDialog('edit');
  }

  function openReviewDialog(item: JsonObject) {
    setSelectedReview(String(item.id ?? ''));
    setReason('');
    setDialog('review');
  }

  function closeDialog() {
    setDialog(null);
  }

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run('创建团队记忆', () => client.createTeamMemory(orgId, createForm), result => {
      setMemories(items => [result, ...items]);
      setCreateForm(emptyTeamMemory);
      selectMemory(result);
      closeDialog();
    });
  }

  function submitEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    void run('编辑团队记忆', () => client.updateMemory(selected, editForm), result => {
      setMemories(items => items.map(item => String(item.id ?? '') === String(result.id ?? '') ? result : item));
      selectMemory(result);
      closeDialog();
    });
  }

  function disableMemory(item: JsonObject) {
    const id = String(item.id ?? '');
    if (!id) {
      return;
    }
    void run('停用团队记忆', () => client.disableMemory(id), result => {
      setMemories(items => items.map(memory => String(memory.id ?? '') === String(result.id ?? '') ? result : memory));
      selectMemory(result);
    });
  }

  function deleteMemory(item: JsonObject) {
    const id = String(item.id ?? '');
    if (!id) {
      return;
    }
    void run('彻底删除记忆', () => client.deleteMemory(id), result => {
      const deletedId = String(result.id ?? id);
      setMemories(items => items.filter(memory => String(memory.id ?? '') !== deletedId));
      if (selected === deletedId) {
        setSelected('');
        setEditForm(emptyTeamMemory);
      }
    });
  }

  function decideReview(action: 'approve' | 'reject') {
    const reviewId = selectedReview.trim();
    if (!reviewId) {
      return;
    }
    const payload = action === 'reject' ? { reason } : {};
    void run(action === 'approve' ? '批准记忆' : '拒绝记忆', () => client.decideReview(reviewId, action, payload), () => {
      setReviews(items => items.filter(item => String(item.id ?? '') !== reviewId));
      setSelectedReview('');
      setReason('');
      closeDialog();
    });
  }

  return (
    <section className="view-stack">
      <div className="view-heading">
        <div>
          <h2>团队记忆库</h2>
          <span>抽取记忆、管理员创建记忆和生命周期治理</span>
        </div>
        <div className="toolbar">
          <SelectField label="状态" value={statusFilter} options={['active', 'archived', 'pending_review', 'rejected', '']} onChange={setStatusFilter} />
          <button className="command" type="button" onClick={() => void refreshMemories()}><RefreshCw size={16} />加载团队记忆</button>
          <button className="command primary" type="button" onClick={openCreateDialog}><Plus size={16} />新建团队记忆</button>
        </div>
      </div>

      <div className="memory-summary-grid">
        <Metric label="全部列表" value={String(memories.length)} />
        <Metric label="自动抽取" value={String(memories.filter(item => String(item.source_type ?? '') === 'auto_extracted').length)} />
        <Metric label="管理员创建" value={String(memories.filter(item => String(item.source_type ?? '') === 'admin_created').length)} />
        <Metric label="当前选中" value={selectedMemory ? String(selectedMemory.id ?? '') : 'none'} />
      </div>

      <div className="memory-workspace">
        <TeamMemoryTable items={memories} selectedId={selected} onEdit={openEditDialog} onDisable={disableMemory} onDelete={deleteMemory} />
        <section className="surface review-queue-card">
          <div className="review-toolbar">
            <SectionTitle icon={Database} title="待审队列" />
            <button className="command" type="button" onClick={() => void refreshReviews()}><RefreshCw size={16} />加载待审</button>
          </div>
          <ReviewQueueTable items={reviews} onReview={openReviewDialog} />
        </section>
      </div>

      {dialog === 'create' && (
        <ModalShell title="创建团队记忆" onClose={closeDialog}>
          <form className="modal-form" onSubmit={submitCreate}>
            <TeamMemoryFields form={createForm} onChange={setCreateForm} placeholder="输入团队级事实、流程、约定或策略。" />
            <div className="modal-actions">
              <button className="command" type="button" onClick={closeDialog}>取消</button>
              <button className="command primary" type="submit"><Plus size={16} />创建团队记忆</button>
            </div>
          </form>
        </ModalShell>
      )}

      {dialog === 'edit' && (
        <ModalShell title="编辑团队记忆" onClose={closeDialog}>
          <form className="modal-form" onSubmit={submitEdit}>
            <Field label="Memory ID" value={selected} onChange={setSelected} readOnly />
            <TeamMemoryFields form={editForm} onChange={setEditForm} />
            <div className="modal-actions">
              <button className="command" type="button" onClick={closeDialog}>取消</button>
              <button className="command primary" type="submit" disabled={!selected}><Save size={16} />保存编辑</button>
            </div>
          </form>
        </ModalShell>
      )}

      {dialog === 'review' && (
        <ModalShell title="审核团队记忆" onClose={closeDialog}>
          <form className="modal-form" onSubmit={event => event.preventDefault()}>
            <Field label="Review ID" value={selectedReview} onChange={setSelectedReview} readOnly />
            <Field label="拒绝理由" value={reason} onChange={setReason} />
            <div className="modal-actions">
              <button className="command" type="button" onClick={closeDialog}>取消</button>
              <button className="command primary" type="button" onClick={() => decideReview('approve')}><CheckCircle2 size={16} />批准</button>
              <button className="command danger" type="button" onClick={() => decideReview('reject')}>拒绝</button>
            </div>
          </form>
        </ModalShell>
      )}
    </section>
  );
}

function TeamMemoryFields({ form, onChange, placeholder }: { form: TeamMemoryForm; onChange: (form: TeamMemoryForm) => void; placeholder?: string }) {
  return (
    <>
      <TextareaField label="记忆内容" value={form.content} onChange={value => onChange({ ...form, content: value })} placeholder={placeholder} />
      <SelectField label="类型" value={form.memoryType} options={['fact', 'policy', 'procedure', 'preference']} onChange={value => onChange({ ...form, memoryType: value })} />
      <SelectField label="敏感度" value={form.sensitivity} options={['normal', 'pii', 'secret', 'restricted']} onChange={value => onChange({ ...form, sensitivity: value })} />
    </>
  );
}

function TeamMemoryTable({ items, selectedId, onEdit, onDisable, onDelete }: { items: JsonObject[]; selectedId: string; onEdit: (item: JsonObject) => void; onDisable: (item: JsonObject) => void; onDelete: (item: JsonObject) => void }) {
  if (items.length === 0) {
    return <div className="surface empty-state">暂无团队记忆。可新建团队记忆或等待客户端自动抽取。</div>;
  }
  return (
    <div className="surface memory-table-wrap">
      <table className="memory-table">
        <thead><tr><th>记忆内容</th><th>来源标签</th><th>状态</th><th>版本</th><th>操作</th></tr></thead>
        <tbody>
          {items.map(item => {
            const id = String(item.id ?? '');
            return (
              <tr key={id} className={id === selectedId ? 'selected-row' : ''}>
                <td><strong>{String(item.content ?? '')}</strong><small>{String(item.memory_type ?? 'fact')} / {String(item.sensitivity ?? 'normal')}</small></td>
                <td><span className={`source-badge ${String(item.source_type ?? '') === 'admin_created' ? 'admin' : 'auto'}`}>{memorySourceLabel(item)}</span><small>{memorySourceDetail(item)}</small></td>
                <td>{String(item.status ?? '')}</td>
                <td>{String(item.version ?? '')}</td>
                <td>
                  <div className="row-actions">
                    <button className="icon-command" type="button" onClick={() => onEdit(item)}>编辑</button>
                    <button className="icon-command" type="button" onClick={() => onDisable(item)}>停用</button>
                    <button className="icon-command danger-text" type="button" onClick={() => onDelete(item)}>删除</button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function ReviewQueueTable({ items, onReview }: { items: JsonObject[]; onReview: (item: JsonObject) => void }) {
  if (items.length === 0) {
    return <div className="empty-state compact">暂无待审记忆。点击“加载待审”刷新队列。</div>;
  }
  return (
    <div className="memory-table-wrap">
      <table className="memory-table review-table">
        <thead><tr><th>Review ID</th><th>Memory ID</th><th>状态</th><th>类型</th><th>操作</th></tr></thead>
        <tbody>
          {items.map(item => (
            <tr key={String(item.id ?? '')}>
              <td>{String(item.id ?? '')}</td>
              <td>{String(item.memory_id ?? '')}</td>
              <td>{String(item.status ?? '')}</td>
              <td>{String(item.review_kind ?? '')}</td>
              <td><button className="icon-command" type="button" onClick={() => onReview(item)}>审核</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function memorySourceLabel(item: JsonObject) {
  return String(item.source_type ?? '') === 'admin_created' ? '管理员创建' : '自动抽取';
}

function memorySourceDetail(item: JsonObject) {
  if (String(item.source_type ?? '') === 'admin_created') {
    return `创建者：${String(item.created_by_member_id ?? '未知管理员')}`;
  }
  return `来源成员：${String(item.source_member_id ?? '未知成员')}`;
}

function TeamSoulView({ orgId, memberId, client, run }: {
  orgId: string;
  memberId: string;
  client: ReturnType<typeof createTeamCloudClient>;
  run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined>;
}) {
  const [teamSoul, setTeamSoul] = useState<JsonObject | null>(null);
  const [runtimeSoul, setRuntimeSoul] = useState<JsonObject | null>(null);
  const [form, setForm] = useState<TeamSoulForm>(emptyTeamSoul);
  const [editorOpen, setEditorOpen] = useState(false);

  function refreshTeamSoul() {
    void run('加载团队父人格', () => client.getTeamSoul(orgId), result => {
      setTeamSoul(result);
      setForm({ content: String(result.content ?? '') });
    }).catch(() => {
      setTeamSoul(null);
      setForm(emptyTeamSoul);
    });
    void run('读取运行时父人格', () => client.getRuntimeTeamSoul(orgId), result => setRuntimeSoul(result)).catch(() => setRuntimeSoul(null));
  }

  useEffect(() => {
    refreshTeamSoul();
  }, [orgId]);

  function openEditor() {
    setForm({ content: String(teamSoul?.content ?? '') });
    setEditorOpen(true);
  }

  function saveTeamSoul(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void run('保存团队父人格', () => client.updateTeamSoul(orgId, {
      content: form.content,
      teamId: orgId,
      updatedBy: memberId
    }), result => {
      setTeamSoul(result);
      setRuntimeSoul(result);
      setForm({ content: String(result.content ?? '') });
      setEditorOpen(false);
      refreshTeamSoul();
    });
  }

  const version = teamSoulValue(teamSoul, 'version', '未配置');
  const checksum = teamSoulValue(teamSoul, 'checksum_sha256', '未生成');
  const updatedAt = teamSoulValue(teamSoul, 'updated_at', '未更新');
  const updatedBy = teamSoulValue(teamSoul, 'updated_by', '未知');

  return (
    <section className="view-stack">
      <div className="view-heading">
        <div>
          <h2>团队父人格治理</h2>
          <span>管理团队级身份、语气和边界准则</span>
        </div>
        <div className="toolbar">
          <button className="command" type="button" onClick={refreshTeamSoul}><RefreshCw size={16} />刷新父人格</button>
          <button className="command primary" type="button" onClick={openEditor}><Pencil size={16} />编辑团队父人格</button>
        </div>
      </div>

      <div className="soul-summary-grid">
        <div className="metric"><span>当前版本</span><strong>版本 {version}</strong></div>
        <div className="metric"><span>Checksum</span><strong>{checksum}</strong></div>
        <div className="metric"><span>更新时间</span><strong>{updatedAt}</strong></div>
        <div className="metric"><span>更新人</span><strong>{updatedBy}</strong></div>
      </div>

      <div className="soul-layout">
        <section className="surface soul-content-card">
          <SectionTitle icon={Sparkles} title="管理态内容" />
          <p>{String(teamSoul?.content ?? '尚未配置团队父人格。')}</p>
        </section>
        <section className="surface soul-content-card">
          <SectionTitle icon={Activity} title="运行时读取" />
          <p>{String(runtimeSoul?.content ?? '运行时暂未读取到团队父人格。')}</p>
          <div className="soul-meta-row">
            <span>runtime v{teamSoulValue(runtimeSoul, 'version', 'none')}</span>
            <code>{teamSoulValue(runtimeSoul, 'checksum_sha256', 'no-checksum')}</code>
          </div>
        </section>
      </div>

      {editorOpen && (
        <ModalShell title="编辑团队父人格" onClose={() => setEditorOpen(false)}>
          <form className="modal-form" onSubmit={saveTeamSoul}>
            <TextareaField label="父人格内容" value={form.content} onChange={value => setForm({ ...form, content: value })} placeholder="定义团队身份、沟通风格、默认边界和必须遵守的团队准则。" />
            <div className="modal-actions">
              <button className="command" type="button" onClick={() => setEditorOpen(false)}>取消</button>
              <button className="command primary" type="submit"><Save size={16} />保存父人格</button>
            </div>
          </form>
        </ModalShell>
      )}
    </section>
  );
}

function teamSoulValue(item: JsonObject | null, key: string, fallback: string) {
  const value = item?.[key];
  if (value === undefined || value === null || value === '') {
    return fallback;
  }
  return String(value);
}

function BackupView({ orgId, client, run }: { orgId: string; client: ReturnType<typeof createTeamCloudClient>; run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined> }) {
  const [memoryPolicy, setMemoryPolicy] = useState({ cadence: 'daily', retentionCount: '7', enabled: true });
  const [soulPolicy, setSoulPolicy] = useState({ cadence: 'weekly', retentionCount: '3', enabled: true });
  const [memoryHistory, setMemoryHistory] = useState<JsonObject[]>([]);
  const [soulHistory, setSoulHistory] = useState<JsonObject[]>([]);
  const [selectedMemoryBackup, setSelectedMemoryBackup] = useState('');
  const [selectedSoulBackup, setSelectedSoulBackup] = useState('');
  const [settingsOpen, setSettingsOpen] = useState<'memory' | 'soul' | null>(null);

  function refreshBackupState() {
    void run('读取团队记忆备份策略', () => client.getTeamBackupPolicy(orgId), result => setMemoryPolicy({
      cadence: String(result.cadence ?? 'daily'),
      retentionCount: String(result.retention_count ?? 7),
      enabled: Boolean(result.enabled)
    }));
    void run('读取团队父人格备份策略', () => client.getTeamSoulBackupPolicy(orgId), result => setSoulPolicy({
      cadence: String(result.cadence ?? 'weekly'),
      retentionCount: String(result.retention_count ?? 3),
      enabled: Boolean(result.enabled)
    }));
    void run('加载团队记忆备份历史', () => client.listTeamBackups(orgId), result => {
      setMemoryHistory(result.items);
      if (!selectedMemoryBackup && result.items.length > 0) {
        setSelectedMemoryBackup(String(result.items[0].id ?? ''));
      }
    });
    void run('加载团队父人格备份历史', () => client.listTeamSoulBackups(orgId), result => {
      setSoulHistory(result.items);
      if (!selectedSoulBackup && result.items.length > 0) {
        setSelectedSoulBackup(String(result.items[0].id ?? ''));
      }
    });
  }

  useEffect(() => {
    refreshBackupState();
  }, [orgId]);

  function savePolicy(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const kind = settingsOpen ?? 'memory';
    const current = kind === 'soul' ? soulPolicy : memoryPolicy;
    const operation = kind === 'soul' ? client.upsertTeamSoulBackupPolicy : client.upsertTeamBackupPolicy;
    void run(kind === 'soul' ? '保存团队父人格备份策略' : '保存团队记忆备份策略', () => operation({
      org_id: orgId,
      cadence: current.cadence,
      enabled: current.enabled,
      retention_count: Number(current.retentionCount)
    }), () => {
      setSettingsOpen(null);
      refreshBackupState();
    });
  }

  function runBackupNow(kind: 'memory' | 'soul') {
    if (kind === 'soul') {
      void run('立即备份团队父人格', () => client.runTeamSoulBackup({ org_id: orgId, team_id: orgId }), result => {
        setSoulHistory(items => [result, ...items]);
        setSelectedSoulBackup(String(result.id ?? ''));
      });
      return;
    }
    void run('立即备份团队记忆', () => client.runTeamBackup({ org_id: orgId }), result => {
      setMemoryHistory(items => [result, ...items]);
      setSelectedMemoryBackup(String(result.id ?? ''));
    });
  }

  function restoreSelected(kind: 'memory' | 'soul') {
    const backupID = kind === 'soul' ? selectedSoulBackup : selectedMemoryBackup;
    if (!backupID) {
      return;
    }
    const operation = kind === 'soul' ? client.restoreTeamSoulBackup : client.restoreTeamBackup;
    void run(kind === 'soul' ? '恢复团队父人格备份' : '恢复团队记忆备份', () => operation(backupID, { org_id: orgId, mode: 'merge' }), () => refreshBackupState());
  }

  const activePolicy = settingsOpen === 'soul' ? soulPolicy : memoryPolicy;
  const setActivePolicy = settingsOpen === 'soul' ? setSoulPolicy : setMemoryPolicy;

  return (
    <section className="view-stack">
      <div className="view-heading">
        <div><h2>备份管理</h2><span>团队记忆与团队父人格备份</span></div>
        <div className="toolbar">
          <button className="command" type="button" onClick={refreshBackupState}><RefreshCw size={16} />刷新</button>
        </div>
      </div>
      <div className="backup-boundary-grid">
        <div className="surface boundary-note"><ShieldCheck size={17} /><span>后端只管理团队记忆和团队父人格，不管理个人记忆。</span></div>
        <div className="surface boundary-note"><ArchiveRestore size={17} /><span>MinIO 是可选备份后端，不是初始化必选组件。</span></div>
      </div>
      <div className="backup-layout">
        <section className="surface tool-panel">
          <SectionTitle icon={Database} title="团队记忆备份" />
          <div className="policy-summary">
            <Metric label="周期" value={memoryPolicy.cadence} />
            <Metric label="保留" value={memoryPolicy.retentionCount} />
            <Metric label="状态" value={memoryPolicy.enabled ? 'enabled' : 'paused'} />
            <Metric label="历史" value={String(memoryHistory.length)} />
          </div>
          <SectionTitle icon={ArchiveRestore} title="团队记忆备份历史" />
          <DataTable
            columns={['Backup ID', '状态', '记忆数', '创建时间']}
            rows={memoryHistory.map(item => [String(item.id ?? ''), String(item.status ?? ''), String(item.item_count ?? 0), String(item.created_at ?? '')])}
            empty="暂无团队记忆备份"
          />
          <div className="toolbar">
            <SelectField label="恢复点" value={selectedMemoryBackup} options={memoryHistory.map(item => String(item.id ?? '')).filter(Boolean)} onChange={setSelectedMemoryBackup} />
            <button className="command" type="button" onClick={() => setSettingsOpen('memory')}><SlidersHorizontal size={16} />记忆备份设置</button>
            <button className="command" type="button" onClick={() => runBackupNow('memory')}><ArchiveRestore size={16} />立即备份记忆</button>
            <button className="command primary" type="button" disabled={!selectedMemoryBackup} onClick={() => restoreSelected('memory')}><ArchiveRestore size={16} />恢复记忆备份</button>
          </div>
        </section>
        <section className="surface tool-panel">
          <SectionTitle icon={Sparkles} title="团队父人格备份" />
          <div className="policy-summary">
            <Metric label="周期" value={soulPolicy.cadence} />
            <Metric label="保留" value={soulPolicy.retentionCount} />
            <Metric label="状态" value={soulPolicy.enabled ? 'enabled' : 'paused'} />
            <Metric label="历史" value={String(soulHistory.length)} />
          </div>
          <SectionTitle icon={ArchiveRestore} title="团队父人格备份历史" />
          <DataTable
            columns={['Backup ID', '状态', '快照数', '创建时间']}
            rows={soulHistory.map(item => [String(item.id ?? ''), String(item.status ?? ''), String(item.item_count ?? 0), String(item.created_at ?? '')])}
            empty="暂无团队父人格备份"
          />
          <div className="toolbar">
            <SelectField label="恢复点" value={selectedSoulBackup} options={soulHistory.map(item => String(item.id ?? '')).filter(Boolean)} onChange={setSelectedSoulBackup} />
            <button className="command" type="button" onClick={() => setSettingsOpen('soul')}><SlidersHorizontal size={16} />父人格备份设置</button>
            <button className="command" type="button" onClick={() => runBackupNow('soul')}><ArchiveRestore size={16} />立即备份父人格</button>
            <button className="command primary" type="button" disabled={!selectedSoulBackup} onClick={() => restoreSelected('soul')}><ArchiveRestore size={16} />恢复父人格备份</button>
          </div>
        </section>
      </div>
      {settingsOpen && (
        <ModalShell title={settingsOpen === 'soul' ? '团队父人格备份设置' : '团队记忆备份设置'} onClose={() => setSettingsOpen(null)}>
          <form className="modal-form" onSubmit={savePolicy}>
            <SelectField label="备份周期" value={activePolicy.cadence} options={['hourly', 'daily', 'weekly', 'monthly']} onChange={value => setActivePolicy({ ...activePolicy, cadence: value })} />
            <Field label="保留份数" value={activePolicy.retentionCount} onChange={value => setActivePolicy({ ...activePolicy, retentionCount: value })} type="number" />
            <label className="toggle"><input type="checkbox" checked={activePolicy.enabled} onChange={event => setActivePolicy({ ...activePolicy, enabled: event.target.checked })} />启用{settingsOpen === 'soul' ? '团队父人格' : '团队记忆'}定时备份</label>
            <div className="modal-actions">
              <button className="command" type="button" onClick={() => setSettingsOpen(null)}>取消</button>
              <button className="command primary" type="submit"><Save size={16} />保存设置</button>
            </div>
          </form>
        </ModalShell>
      )}
    </section>
  );
}

function AuditView({ orgId, client, run }: { orgId: string; client: ReturnType<typeof createTeamCloudClient>; run: <T>(label: string, operation: () => Promise<T>, onSuccess?: (result: T) => void) => Promise<T | undefined> }) {
  const [events, setEvents] = useState<JsonObject[]>([]);
  const [limit, setLimit] = useState('50');
  return (
    <section className="view-stack">
      <div className="view-heading">
        <h2>审计时间线</h2>
        <div className="toolbar"><Field label="条数" value={limit} onChange={setLimit} type="number" /><button className="command" type="button" onClick={() => void run('加载审计', () => client.auditEvents(orgId, Number(limit)), result => setEvents(result.items))}><RefreshCw size={16} />加载审计</button></div>
      </div>
      <DataTable columns={['Actor', 'Action', 'Resource', 'Decision']} rows={events.map(item => [String(item.actor_id ?? ''), String(item.action ?? ''), String(item.resource ?? ''), String(item.decision ?? '')])} empty="暂无审计事件" />
    </section>
  );
}

function LocalConnectionView({ apiBase, member }: { apiBase: string; member: StoredMember }) {
  const url = apiBase || 'http://localhost:8780';
  return (
    <section className="view-stack">
      <div className="view-heading"><h2>本地连接</h2><span>{member.id}</span></div>
      <div className="connection-grid">
        <OutputBlock title="Team Cloud URL" value={url} />
        <OutputBlock title="Dashboard URL" value={`${url}/dashboard/`} />
        <OutputBlock title="Hermes CLI" value={`HERMES_TEAM_CLOUD_URL=${url} hermes`} />
        <OutputBlock title="团队上下文" value={`${member.org_id} / ${member.id}`} />
      </div>
    </section>
  );
}

function ModalShell({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="modal-backdrop">
      <section className="modal-panel" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-header">
          <h2>{title}</h2>
          <button className="icon-command" type="button" aria-label="关闭弹窗" onClick={onClose}><X size={16} /></button>
        </div>
        {children}
      </section>
    </div>
  );
}

function SectionTitle({ icon: Icon, title }: { icon: typeof ShieldCheck; title: string }) {
  return <div className="section-title"><Icon size={18} /><h2>{title}</h2></div>;
}

function Field({ label, value, onChange, type = 'text', placeholder, readOnly = false }: { label: string; value: string; onChange: (value: string) => void; type?: string; placeholder?: string; readOnly?: boolean }) {
  return <label className="field"><span>{label}</span><input type={type} value={value} placeholder={placeholder} readOnly={readOnly} onChange={event => onChange(event.target.value)} /></label>;
}

function TextareaField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="field"><span>{label}</span><textarea value={value} placeholder={placeholder} onChange={event => onChange(event.target.value)} /></label>;
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label className="field"><span>{label}</span><select value={value} onChange={event => onChange(event.target.value)}>{options.map(option => <option key={option} value={option}>{option}</option>)}</select></label>;
}

function SetupCheck({ title, ok, detail }: { title: string; ok: boolean; detail: string }) {
  return <div className={ok ? 'setup-check ok' : 'setup-check'}><span>{ok ? 'ready' : 'required'}</span><strong>{title}</strong><small>{detail}</small></div>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function StatusPanel({ title, rows }: { title: string; rows: Array<[string, unknown]> }) {
  return <div className="surface status-panel"><h3>{title}</h3>{rows.map(([label, value]) => <div key={label} className="status-row"><span>{label}</span><strong>{value === true ? 'ready' : 'attention'}</strong></div>)}</div>;
}

function DataTable({ columns, rows, empty }: { columns: string[]; rows: string[][]; empty: string }) {
  if (rows.length === 0) {
    return <div className="surface empty-state">{empty}</div>;
  }
  return (
    <div className="surface table-wrap">
      <table>
        <thead><tr>{columns.map(column => <th key={column}>{column}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, cellIndex) => <td key={`${index}-${cellIndex}`}>{cell}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

function MembersTable({ items, onEdit, onDisable }: { items: JsonObject[]; onEdit: (item: JsonObject) => void; onDisable: (item: JsonObject) => void }) {
  if (items.length === 0) {
    return <div className="surface empty-state">暂无匹配成员</div>;
  }
  return (
    <div className="surface table-wrap">
      <table>
        <thead><tr><th>帐号</th><th>邮箱</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          {items.map(item => (
            <tr key={String(item.id ?? item.user_id)}>
              <td>{String(item.user_id ?? '')}</td>
              <td>{String(item.email ?? '')}</td>
              <td>{String(item.role ?? '')}</td>
              <td>{String(item.status ?? '')}</td>
              <td>
                <div className="row-actions">
                  <button className="icon-command" type="button" aria-label={`编辑 ${String(item.user_id ?? '')}`} onClick={() => onEdit(item)}><Pencil size={15} /></button>
                  <button className="icon-command danger" type="button" aria-label={`停用 ${String(item.user_id ?? '')}`} disabled={String(item.role ?? '') === 'super_admin' || String(item.status ?? '') === 'suspended'} onClick={() => onDisable(item)}>停用</button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OutputBlock({ title, value }: { title: string; value: string }) {
  return <div className="output-block"><span>{title}</span><code>{value}</code><button className="icon-command" type="button" aria-label={`复制 ${title}`} onClick={() => void navigator.clipboard?.writeText(value)}><Clipboard size={15} /></button></div>;
}

function ResultStrip({ action, fallback, compact = false }: { action: ActionState; fallback: unknown; compact?: boolean }) {
  return (
    <section className={compact ? `result-strip compact result-${action.status}` : `result-strip result-${action.status}`} aria-live="polite">
      <div><strong>{action.label}</strong><span>{action.status}</span></div>
      <pre>{action.detail || jsonSummary(fallback)}</pre>
    </section>
  );
}
