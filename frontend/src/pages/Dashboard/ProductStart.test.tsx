import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProductStart from './ProductStart';
vi.mock('@/services/request', () => ({default: {get: vi.fn().mockResolvedValue({asset_count:0,running_tasks:0,pending_reviews:0,qualified_versions:0,experiment_count:0,training_ready:false,recent_tasks:[]})}}));
describe('工作台业务入口', () => {
  it('新建治理任务先进入数据选择，不直接创建任务', () => {
    render(<MemoryRouter initialEntries={['/app/dashboard']}><Routes><Route path="/app/dashboard" element={<ProductStart />} /><Route path="/app/data-governance/sources" element={<div>选择数据页面</div>} /></Routes></MemoryRouter>);
    fireEvent.click(screen.getByRole('button',{name:'新建数据治理任务'}));
    expect(screen.getByText('选择数据页面')).toBeInTheDocument();
  });
});
