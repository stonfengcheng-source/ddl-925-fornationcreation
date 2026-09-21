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
    // 缺少 taskId 时应结束加载并给出明确提示，而不是永久显示 loading。
    expect(screen.getByText('任务不存在或无训练数据')).toBeInTheDocument();
  });
});
