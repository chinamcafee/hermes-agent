import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TeamCloudDashboard from './page';

describe('TeamCloudDashboard', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('renders the server initialization and administration surfaces', () => {
    render(<TeamCloudDashboard />);

    expect(screen.getByRole('heading', { name: 'Team Cloud Admin' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /初始化/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /组织/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /权限/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /记忆治理/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /备份/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /审计/ })).toBeInTheDocument();
  });

  it('stores connection settings in session storage by default', async () => {
    render(<TeamCloudDashboard />);

    await userEvent.clear(screen.getByLabelText('API 地址'));
    await userEvent.type(screen.getByLabelText('API 地址'), 'http://localhost:8780');
    await userEvent.type(screen.getByLabelText('Service token'), 'dev-token');

    expect(sessionStorage.getItem('teamCloudDashboard.apiBase')).toBe('http://localhost:8780');
    expect(sessionStorage.getItem('teamCloudDashboard.token')).toBe('dev-token');
  });

  it('shows the bootstrap form fields needed for first-run super admin creation', () => {
    render(<TeamCloudDashboard />);

    expect(screen.getByLabelText('组织标识')).toBeInTheDocument();
    expect(screen.getByLabelText('组织名称')).toBeInTheDocument();
    expect(screen.getByLabelText('管理员邮箱')).toBeInTheDocument();
    expect(screen.getByLabelText('管理员用户 ID')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '创建超级管理员' })).toBeInTheDocument();
  });
});
