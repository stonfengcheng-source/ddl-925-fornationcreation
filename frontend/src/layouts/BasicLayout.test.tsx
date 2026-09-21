import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import BasicLayout from './BasicLayout';
import { ConfigProvider } from 'antd';
import { geekNotionTheme } from '@/theme/geek-notion';

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
    
    // 验证侧边栏背景色是否符合 Geek+Notion 主题 (米色 #F7F7F5)
    // 注意：AntD 会将 Token 转换为 CSS 变量或具体样式，这里主要验证结构
    expect(sider).toHaveClass('ant-layout-sider-light');
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
    expect(screen.getByText('工作台')).toBeInTheDocument();
    expect(screen.getByText('个人中心')).toBeInTheDocument();
  });
});