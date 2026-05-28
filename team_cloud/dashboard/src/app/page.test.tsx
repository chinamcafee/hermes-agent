import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import TeamCloudDashboard from './page';

function jsonResponse(payload: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' }
  }));
}

describe('TeamCloudDashboard', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.restoreAllMocks();
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      initialized: false,
      organization_count: 0,
      super_admin_count: 0,
      checks: {
        postgres_configured: false,
        minio_configured: false,
        backend: true,
        authz: true,
        dashboard: true
      }
    })));
  });

  it('renders an independent initialization guide before the service is initialized', async () => {
    render(<TeamCloudDashboard />);

    expect(await screen.findByRole('heading', { name: 'Team Cloud 初始化引导' })).toBeInTheDocument();
    expect(screen.getByText('步骤 1 / 3')).toBeInTheDocument();
    expect(screen.getByLabelText('团队名称')).toBeInTheDocument();
    expect(screen.queryByText('默认工作组')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('工作组标识')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Service token')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('PostgreSQL DSN')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('MinIO Endpoint')).not.toBeInTheDocument();
    expect(screen.queryByRole('navigation', { name: 'Team Cloud 管理导航' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '组织' })).not.toBeInTheDocument();
  });

  it('stores only the API base during initialization', async () => {
    render(<TeamCloudDashboard />);

    await userEvent.clear(await screen.findByLabelText('API 地址'));
    await userEvent.type(screen.getByLabelText('API 地址'), 'http://localhost:8780');

    expect(sessionStorage.getItem('teamCloudDashboard.apiBase')).toBe('http://localhost:8780');
    expect(sessionStorage.getItem('teamCloudDashboard.serviceToken')).toBeNull();
  });

  it('shows a login page after initialization instead of bootstrap tabs', async () => {
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      initialized: true,
      organization_count: 1,
      super_admin_count: 1,
      checks: {
        postgres_configured: true,
        minio_configured: true,
        backend: true,
        authz: true,
        dashboard: true
      }
    })));

    render(<TeamCloudDashboard />);

    expect(await screen.findByRole('heading', { name: '管理台登录' })).toBeInTheDocument();
    expect(screen.getByLabelText('帐号')).toBeInTheDocument();
    expect(screen.getByLabelText('密码')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '初始化' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '组织' })).not.toBeInTheDocument();
  });

  it('renders professional admin surfaces when a dashboard session exists', async () => {
    sessionStorage.setItem('teamCloudDashboard.sessionToken', 'hcs_session_token');
    sessionStorage.setItem('teamCloudDashboard.member', JSON.stringify({
      id: 'hermes-labs:owner',
      org_id: 'hermes-labs',
      role: 'super_admin',
      display_name: 'Owner Example'
    }));
    vi.stubGlobal('fetch', vi.fn(() => jsonResponse({
      initialized: true,
      organization_count: 1,
      super_admin_count: 1,
      checks: {
        postgres_configured: true,
        minio_configured: true,
        backend: true,
        authz: true,
        dashboard: true
      }
    })));

    render(<TeamCloudDashboard />);

    expect(await screen.findByRole('heading', { name: '团队运营概览' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Team Cloud 管理导航' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /团队成员/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /权限中心/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /记忆治理/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /团队父人格中心/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /备份管理/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /审计时间线/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /本地连接/ })).toBeInTheDocument();
    expect(screen.getByText(/团队父人格配置中心已内置在管理台/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '组织' })).not.toBeInTheDocument();
  });

  it('opens create, edit, and review memory workflows in dialogs', async () => {
    sessionStorage.setItem('teamCloudDashboard.sessionToken', 'hcs_session_token');
    sessionStorage.setItem('teamCloudDashboard.member', JSON.stringify({
      id: 'hermes-labs:owner',
      org_id: 'hermes-labs',
      role: 'super_admin',
      display_name: 'Owner Example'
    }));
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/v1/bootstrap/status')) {
        return jsonResponse({
          initialized: true,
          organization_count: 1,
          super_admin_count: 1,
          checks: {
            postgres_configured: true,
            minio_configured: true,
            backend: true,
            authz: true,
            dashboard: true
          }
        });
      }
      if (url.includes('/v1/memory/review')) {
        return jsonResponse({
          items: [
            {
              id: 'review-auto',
              memory_id: 'mem-auto',
              status: 'pending',
              review_kind: 'team_memory'
            }
          ]
        });
      }
      if (url.includes('/v1/memory?')) {
        return jsonResponse({
          items: [
            {
              id: 'mem-auto',
              content: '团队统一使用蓝绿发布。',
              status: 'active',
              memory_type: 'procedure',
              sensitivity: 'normal',
              source_type: 'auto_extracted',
              source_member_id: 'hermes-labs:alice',
              version: 1
            },
            {
              id: 'mem-admin',
              content: '事故复盘必须记录 owner。',
              status: 'active',
              memory_type: 'policy',
              sensitivity: 'normal',
              source_type: 'admin_created',
              created_by_member_id: 'hermes-labs:owner',
              version: 1
            }
          ]
        });
      }
      return jsonResponse({ items: [] });
    }));

    render(<TeamCloudDashboard />);

    await userEvent.click(await screen.findByRole('button', { name: /记忆治理/ }));

    expect(screen.getByRole('heading', { name: '团队记忆库' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /加载团队记忆/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /新建团队记忆/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /加载待审/ })).toBeInTheDocument();
    expect(screen.getAllByText('自动抽取').length).toBeGreaterThan(0);
    expect(screen.getAllByText('管理员创建').length).toBeGreaterThan(0);
    expect(screen.queryByRole('textbox', { name: '记忆内容' })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '审核操作' })).not.toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /新建团队记忆/ }));
    expect(screen.getByRole('dialog', { name: '创建团队记忆' })).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: '记忆内容' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '关闭弹窗' }));

    expect(await screen.findByText('团队统一使用蓝绿发布。')).toBeInTheDocument();
    expect(screen.getByText('来源成员：hermes-labs:alice')).toBeInTheDocument();
    expect(screen.getByText('创建者：hermes-labs:owner')).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('button', { name: '编辑' })[0]);
    expect(screen.getByRole('dialog', { name: '编辑团队记忆' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('团队统一使用蓝绿发布。')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '关闭弹窗' }));

    await userEvent.click(screen.getByRole('button', { name: /加载待审/ }));
    expect(await screen.findByText('review-auto')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '审核' }));
    expect(screen.getByRole('dialog', { name: '审核团队记忆' })).toBeInTheDocument();
    expect(screen.getByDisplayValue('review-auto')).toBeInTheDocument();
  });

  it('renders backup management for team memory and team soul history and settings', async () => {
    sessionStorage.setItem('teamCloudDashboard.sessionToken', 'hcs_session_token');
    sessionStorage.setItem('teamCloudDashboard.member', JSON.stringify({
      id: 'hermes-labs:owner',
      org_id: 'hermes-labs',
      role: 'super_admin',
      display_name: 'Owner Example'
    }));
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/v1/bootstrap/status')) {
        return jsonResponse({
          initialized: true,
          organization_count: 1,
          super_admin_count: 1,
          checks: {
            postgres_configured: true,
            minio_configured: false,
            backend: true,
            authz: true,
            dashboard: true
          }
        });
      }
      if (url.includes('/v1/team-memory-backup-policy')) {
        return jsonResponse({ org_id: 'hermes-labs', cadence: 'daily', enabled: true, retention_count: 3 });
      }
      if (url.includes('/v1/team-soul-backup-policy')) {
        return jsonResponse({ org_id: 'hermes-labs', cadence: 'weekly', enabled: true, retention_count: 2 });
      }
      if (url.includes('/v1/backups/team-soul')) {
        return jsonResponse({ items: [{ id: 'backup-soul-1', item_count: 1, status: 'completed', created_at: '2026-05-24T10:30:00Z' }] });
      }
      if (url.includes('/v1/backups/team')) {
        return jsonResponse({ items: [{ id: 'backup-team-1', item_count: 2, status: 'completed', created_at: '2026-05-24T10:00:00Z' }] });
      }
      return jsonResponse({ items: [] });
    }));

    render(<TeamCloudDashboard />);

    await userEvent.click(await screen.findByRole('button', { name: /备份管理/ }));

    expect(await screen.findByRole('heading', { name: '备份管理' })).toBeInTheDocument();
    expect(screen.getByText('团队记忆备份')).toBeInTheDocument();
    expect(screen.getByText('团队父人格备份')).toBeInTheDocument();
    expect(screen.getByText('后端只管理团队记忆和团队父人格，不管理个人记忆。')).toBeInTheDocument();
    expect(screen.getByText('MinIO 是可选备份后端，不是初始化必选组件。')).toBeInTheDocument();
    expect(screen.getByText('团队记忆备份历史')).toBeInTheDocument();
    expect(screen.getByText('团队父人格备份历史')).toBeInTheDocument();
    expect(screen.getAllByText('backup-team-1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('backup-soul-1').length).toBeGreaterThan(0);
    expect(screen.queryByText('成员备份策略')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('成员 ID')).not.toBeInTheDocument();
  });

  it('loads team soul metadata and edits content in a modal', async () => {
    sessionStorage.setItem('teamCloudDashboard.sessionToken', 'hcs_session_token');
    sessionStorage.setItem('teamCloudDashboard.member', JSON.stringify({
      id: 'hermes-labs:owner',
      org_id: 'hermes-labs',
      role: 'super_admin',
      display_name: 'Owner Example'
    }));
    const calls: Array<{ url: string; init?: RequestInit }> = [];
    vi.stubGlobal('fetch', vi.fn((url: string, init?: RequestInit) => {
      calls.push({ url, init });
      if (url.includes('/v1/bootstrap/status')) {
        return jsonResponse({
          initialized: true,
          organization_count: 1,
          super_admin_count: 1,
          checks: {
            postgres_configured: true,
            minio_configured: false,
            backend: true,
            authz: true,
            dashboard: true
          }
        });
      }
      if (url.endsWith('/v1/team-soul') && init?.method === 'PUT') {
        return jsonResponse({
          org_id: 'hermes-labs',
          team_id: 'hermes-labs',
          content: '团队父人格：保存后的治理准则。',
          version: 4,
          checksum_sha256: 'sha256-updated-team-soul',
          updated_at: '2026-05-24T11:00:00Z',
          updated_by: 'hermes-labs:owner'
        });
      }
      if (url.includes('/v1/runtime/team-soul')) {
        return jsonResponse({
          org_id: 'hermes-labs',
          team_id: 'hermes-labs',
          content: '运行时团队父人格：保持专业、透明、边界明确。',
          version: 3,
          checksum_sha256: 'sha256-current-team-soul',
          updated_at: '2026-05-24T10:00:00Z',
          updated_by: 'hermes-labs:owner'
        });
      }
      if (url.includes('/v1/team-soul')) {
        return jsonResponse({
          org_id: 'hermes-labs',
          team_id: 'hermes-labs',
          content: '团队父人格：保持专业、透明、边界明确。',
          version: 3,
          checksum_sha256: 'sha256-current-team-soul',
          updated_at: '2026-05-24T10:00:00Z',
          updated_by: 'hermes-labs:owner'
        });
      }
      return jsonResponse({ items: [] });
    }));

    render(<TeamCloudDashboard />);

    await userEvent.click(await screen.findByRole('button', { name: /团队父人格/ }));

    expect(await screen.findByRole('heading', { name: '团队父人格治理' })).toBeInTheDocument();
    expect(screen.getByText('版本 3')).toBeInTheDocument();
    expect(screen.getAllByText('sha256-current-team-soul').length).toBeGreaterThan(0);
    expect(screen.getByText('2026-05-24T10:00:00Z')).toBeInTheDocument();
    expect(screen.getByText('运行时团队父人格：保持专业、透明、边界明确。')).toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: '父人格内容' })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /编辑团队父人格/ }));
    expect(screen.getByRole('dialog', { name: '编辑团队父人格' })).toBeInTheDocument();
    const content = screen.getByRole('textbox', { name: '父人格内容' });
    expect(content).toHaveValue('团队父人格：保持专业、透明、边界明确。');

    await userEvent.clear(content);
    await userEvent.type(content, '团队父人格：保存后的治理准则。');
    await userEvent.click(screen.getByRole('button', { name: /保存父人格/ }));

    await waitFor(() => expect(calls.some(call => call.init?.method === 'PUT' && call.url.endsWith('/v1/team-soul'))).toBe(true));
    const saveCall = calls.find(call => call.init?.method === 'PUT' && call.url.endsWith('/v1/team-soul'));
    expect(JSON.parse(String(saveCall?.init?.body))).toMatchObject({
      org_id: 'hermes-labs',
      team_id: 'hermes-labs',
      content: '团队父人格：保存后的治理准则。'
    });
  });
});
