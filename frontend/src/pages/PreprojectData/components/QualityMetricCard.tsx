import { Button, Tag, Typography } from 'antd';
import type { Metric } from '../types';
import { METRIC_METADATA } from '../types/metricMetadata';

const labels: Record<string,string> = {mathematics:'数学',language:'语言',science:'科学',programming:'编程',other:'其他',other_unclassified:'其他或未分类',unknown:'未知',min:'最小值',median:'中位数',max:'最大值',count:'数量',categories:'类别',share_threshold:'占比阈值',invalid_date_count:'无效日期',future_date_count:'未来日期'};
export function formatMetric(name: string, value: unknown): string {
  if (value === null || value === undefined) return 'N/A';
  if (typeof value === 'number') return METRIC_METADATA[name]?.type === 'ratio' ? `${(value * 100).toFixed(2)}%` : value.toLocaleString(undefined,{maximumFractionDigits:6});
  return typeof value === 'object' ? '查看分布详情' : String(value);
}
function StructuredValue({value, name}: {value: unknown; name:string}) {
  if (Array.isArray(value)) return <span>{value.length ? value.map(item => labels[String(item)] || String(item)).join('、') : '无'}</span>;
  if (value && typeof value === 'object') return <dl className="metric-distribution">{Object.entries(value).map(([key,item]) => <div key={key}><dt title={key}>{labels[key] || key}</dt><dd>{typeof item === 'object' && item !== null ? <StructuredValue value={item} name={name} /> : <>{formatMetric(key,item)}{name === 'data_age_days' ? ' 天' : ''}</>}</dd></div>)}</dl>;
  return <>{formatMetric(name,value)}</>;
}
export function QualityMetricCard({ name, metric, onSample }: { name: string; metric: Metric; onSample?: (id:string) => void }) {
  const info = METRIC_METADATA[name];
  if (!info) return <div className="metric-detail"><Typography.Text type="secondary">存在未配置说明的指标，暂不解释。</Typography.Text></div>;
  return <div className="metric-detail"><div className="metric-detail-title"><strong>{info.name}</strong><Tag color={metric.value === null || metric.value === undefined ? 'default' : 'blue'}>{metric.value === null || metric.value === undefined ? '暂无依据' : '已计算'}</Tag></div>
    <Typography.Paragraph type="secondary" style={{margin:'4px 0'}}>{info.description}</Typography.Paragraph>
    <div className="metric-value"><StructuredValue value={metric.value} name={name} /></div>
    {metric.value === null || metric.value === undefined ? <Typography.Paragraph type="secondary">{info.unavailable}</Typography.Paragraph> : <Typography.Text type="secondary">分子 / 分母：{metric.numerator ?? 'N/A'} / {metric.denominator ?? 'N/A'} · {info.direction}</Typography.Text>}
    <details><summary>计算依据与适用范围</summary><p>计算方式：{info.formula}</p><p>适用范围：{info.applicability}</p>{metric.issue_sample_ids?.length ? <p>关联异常样本：{metric.issue_sample_ids.length} 条 {onSample && <Button size="small" onClick={() => onSample(metric.issue_sample_ids![0])}>查看样本</Button>}</p> : null}</details>
  </div>;
}
