import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import LegacyBusinessRedirect from './LegacyBusinessRedirect';

const Location = () => { const location = useLocation(); return <div>{location.pathname}{location.search}{location.hash}</div>; };
describe('旧业务链接', () => {
  it('重定向时保留治理阶段、任务和版本参数', () => {
    render(<MemoryRouter initialEntries={['/app/preproject-data/quality?source_id=s1&task_id=t1&version_id=v1#report']}><Routes>
      <Route path="/app/preproject-data/:section" element={<LegacyBusinessRedirect oldPath="/app/preproject-data" newPath="/app/data-governance" />} />
      <Route path="/app/data-governance/:section" element={<Location />} />
    </Routes></MemoryRouter>);
    expect(screen.getByText('/app/data-governance/quality?source_id=s1&task_id=t1&version_id=v1#report')).toBeInTheDocument();
  });
});
