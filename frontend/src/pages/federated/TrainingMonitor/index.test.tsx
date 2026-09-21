import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TrainingMonitor from './index';

describe('TrainingMonitor', () => {
  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <TrainingMonitor />
      </BrowserRouter>
    );
    // 页面加载时应该显示 loading 状态
    expect(screen.getByText(/加载训练监控数据/i)).toBeDefined();
  });
});
