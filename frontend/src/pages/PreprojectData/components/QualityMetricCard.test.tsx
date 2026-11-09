import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { QualityMetricCard } from './QualityMetricCard';

describe('质量指标中文展示', () => {
  it('对象指标按类别展示，不输出原始 JSON，长类别可换行', () => {
    const longName = 'very-long-source-identifier-'.repeat(8);
    const { container } = render(<QualityMetricCard name="source_distribution" metric={{value:{[longName]:12,mathematics:3},numerator:null,denominator:null}} />);
    expect(screen.getByText('来源分布')).toBeInTheDocument();
    expect(screen.getByText(longName)).toBeInTheDocument();
    expect(screen.getByText('数学')).toBeInTheDocument();
    expect(screen.queryByText(/\{"/)).not.toBeInTheDocument();
    expect(container.querySelector('.metric-distribution')).toBeInTheDocument();
  });
  it('不可测指标说明原因，数值不误显示为零', () => {
    render(<QualityMetricCard name="reference_distribution_difference" metric={{value:null,numerator:null,denominator:null}} />);
    expect(screen.getByText('参考分布差异')).toBeInTheDocument();
    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.getByText(/缺少可靠的参考分布/)).toBeInTheDocument();
  });
  it('熵使用数值而不是百分比', () => {
    render(<QualityMetricCard name="normalized_category_entropy" metric={{value:.75,numerator:null,denominator:null}} />);
    expect(screen.getByText('0.75')).toBeInTheDocument();
    expect(screen.queryByText('75.00%')).not.toBeInTheDocument();
  });
});
