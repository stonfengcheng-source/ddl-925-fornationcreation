import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Layout } from './Layout';

// Mock Lucide icons used in Layout
vi.mock('lucide-react', () => ({
  LayoutDashboard: () => <span data-testid="icon-dashboard" />,
  ListTodo: () => <span data-testid="icon-tasks" />,
  User: () => <span data-testid="icon-user" />,
  LogOut: () => <span data-testid="icon-logout" />,
  Menu: () => <span data-testid="icon-menu" />,
}));

// Mock useUserStore
const mockLogout = vi.fn();
vi.mock('@/store/useUserStore', () => ({
  useUserStore: (selector: any) => {
    if (typeof selector === 'function') {
      return selector({ logout: mockLogout });
    }
    return { logout: mockLogout };
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
    expect(screen.getByText('工作台')).toBeInTheDocument();
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
