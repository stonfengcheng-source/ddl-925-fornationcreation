import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import RevenueShare from './index';

describe('RevenueShare', () => {
  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <RevenueShare />
      </BrowserRouter>
    );
    // 缺少 taskId 时应结束加载并给出明确提示，而不是永久显示 loading。
    expect(screen.getByText('暂无贡献度数据')).toBeInTheDocument();
  });
});
