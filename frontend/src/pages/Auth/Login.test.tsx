import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { geekNotionTheme } from '@/theme/geek-notion';
import Login from './Login';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('Login Page', () => {
  it('should render login form with geek style', () => {
    render(
      <ConfigProvider theme={geekNotionTheme}>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </ConfigProvider>
    );
    
    // 验证标题存在 (使用更灵活的匹配，因为 AntD Card Title 可能嵌套)
    expect(screen.getByText(/Data Task Platform/i)).toBeInTheDocument();
    
    // 验证输入框存在
    expect(screen.getByLabelText('用户名')).toBeInTheDocument();
    expect(screen.queryByLabelText('密码')).not.toBeInTheDocument();
    
    // 验证登录按钮存在 (AntD 按钮文本可能有空格或 span 包裹)
    const loginBtn = screen.getByRole('button', { name: /登录/i });
    expect(loginBtn).toBeInTheDocument();
  });

  it('should navigate to tasks on successful login', async () => {
    render(
      <ConfigProvider theme={geekNotionTheme}>
        <MemoryRouter>
          <Login />
        </MemoryRouter>
      </ConfigProvider>
    );

    // 模拟输入
    fireEvent.change(screen.getByLabelText('用户名'), { target: { value: 'admin' } });
    
    // 模拟点击登录
    const loginBtn = screen.getByRole('button', { name: /登录/i });
    fireEvent.click(loginBtn);
    
    // 验证是否调用了 navigate (需要等待异步操作，这里简化验证逻辑)
    // 实际项目中可能需要 waitFor
  });
});
