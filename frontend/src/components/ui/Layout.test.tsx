import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from './Layout';

// Mock Lucide icons used in Layout
vi.mock('lucide-react', () => ({
  LayoutDashboard: () => <span data-testid="icon-dashboard" />,
  ListTodo: () => <span data-testid="icon-tasks" />,
  PlusCircle: () => <span data-testid="icon-plus" />,
  FolderOpen: () => <span data-testid="icon-folder" />,
  User: () => <span data-testid="icon-user" />,
  Wallet: () => <span data-testid="icon-wallet" />,
  Bell: () => <span data-testid="icon-bell" />,
  ShieldCheck: () => <span data-testid="icon-shield-check" />,
  HardDrive: () => <span data-testid="icon-hard-drive" />,
  Sparkles: () => <span data-testid="icon-sparkles" />,
  Shield: () => <span data-testid="icon-shield" />,
  Settings: () => <span data-testid="icon-settings" />,
  Users: () => <span data-testid="icon-users" />,
  LogOut: () => <span data-testid="icon-logout" />,
  Menu: () => <span data-testid="icon-menu" />,
}));

// Mock useUserStore
const mockLogout = vi.fn();
const mockUser = {
  userId: 'dev-user',
  username: 'admin',
  email: '',
  role: 'admin',
};
vi.mock('@/store/useUserStore', () => ({
  useUserStore: (selector: any) => {
    if (typeof selector === 'function') {
      return selector({ logout: mockLogout, user: mockUser });
    }
    return { logout: mockLogout, user: mockUser };
  },
}));

describe('Layout Component', () => {
  it('renders sidebar and header', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    
    expect(screen.getByText('Data Task Platform')).toBeInTheDocument();
    expect(screen.getByText('任务大厅')).toBeInTheDocument();
    expect(screen.getAllByText('工作台').length).toBeGreaterThan(0);
    expect(screen.getByText('个人中心')).toBeInTheDocument();
  });

  it('renders logout button', () => {
    render(
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    );
    
    expect(screen.getByText('退出登录')).toBeInTheDocument();
  });
});
