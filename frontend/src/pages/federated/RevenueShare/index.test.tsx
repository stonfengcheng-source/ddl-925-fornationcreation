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
    // 页面加载时应该显示 loading 状态
    expect(screen.getByText(/加载分账数据/i)).toBeDefined();
  });
});
