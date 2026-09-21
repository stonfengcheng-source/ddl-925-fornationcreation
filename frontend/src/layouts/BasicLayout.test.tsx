import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BasicLayout from './BasicLayout';
import { ConfigProvider } from 'antd';
import { geekNotionTheme } from '@/theme/geek-notion';
import { useUserStore } from '@/store/useUserStore';

// Mock matchMedia for Ant Design
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('BasicLayout Component', () => {
  beforeEach(() => {
    useUserStore.setState({
      user: { userId: 'dev-user', username: 'admin', email: '', role: 'admin' },
      token: 'dev-token',
      isAuthenticated: true,
    });
  });

  afterEach(() => {
    useUserStore.getState().logout();
  });

  it('should render side menu with correct theme style', () => {
    render(
      <ConfigProvider theme={geekNotionTheme}>
        <MemoryRouter>
          <BasicLayout />
        </MemoryRouter>
      </ConfigProvider>
    );
    
    // 验证侧边栏是否存在
    const sider = document.querySelector('aside');
    expect(sider).toBeInTheDocument();
    
    // 当前布局使用 Notion 风格 Tailwind 类，而不是 Ant Design Layout Sider。
    expect(sider).toHaveClass('bg-background-secondary');
  });

  it('should render navigation items', () => {
    render(
      <ConfigProvider theme={geekNotionTheme}>
        <MemoryRouter>
          <BasicLayout />
        </MemoryRouter>
      </ConfigProvider>
    );
    
    expect(screen.getByText('任务大厅')).toBeInTheDocument();
    expect(screen.getAllByText('工作台').length).toBeGreaterThan(0);
    expect(screen.getByText('个人中心')).toBeInTheDocument();
  });
});
