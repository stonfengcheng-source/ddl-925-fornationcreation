import * as React from 'react';
import { useSearchParams } from 'react-router-dom';
import { Alert, Button, Card, Col, Row, Space, Statistic, Tag, Typography } from 'antd';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { downloadGovernanceReport, getPreprojectReport, getPreprojectResults, getPreprojectSamples } from '@/services/api/preprojectData';
import { useWorkspace } from '../layout/PreprojectLayout';
import { useResource } from '../hooks/useResource';
import { QualityMetricCard, formatMetric } from '../components/QualityMetricCard';
import { DIMENSION_PRIMARY, METRIC_METADATA } from '../types/metricMetadata';
import type { Metric } from '../types';

const labels: Record<string,string> = {completeness:'完整性',consistency:'一致性',diversity:'多元性',unbiasedness:'无偏性',timeliness:'时效性'};
const states: Record<string,string> = {keep:'合格候选',review:'待复核',quarantine:'隔离',drop:'剔除',repair_pending:'待修复'};
const fieldNames: Record<string,string> = {instruction:'问题 / 指令',input:'上下文',output:'回答 / 输出',system:'系统说明'};
function metricValue(key:string, item:unknown): Metric | null {
  if (typeof item === 'number') return {value:item,numerator:null,denominator:null};
  if (!item || typeof item !== 'object') return null;
  if ('value' in item) return item as Metric;
  if (key === 'category_distribution' && 'counts' in item) return {value:(item as {counts:unknown}).counts,numerator:null,denominator:null};
  return null;
}
export function QualityPage() {
  const {taskId,task,go} = useWorkspace(); const [params,setParams] = useSearchParams(); const issue=params.get('issue') || '';
  const [offset,setOffset] = React.useState(0);
  const resultLoader=React.useCallback((signal:AbortSignal)=>getPreprojectResults(taskId,signal),[taskId]);
  const sampleLoader=React.useCallback((signal:AbortSignal)=>getPreprojectSamples(taskId,offset,issue,signal),[taskId,offset,issue]);
  const enabled=task?.task_id===taskId && task.status==='completed';
  const result=useResource(taskId,enabled,resultLoader);
  const reportLoader=React.useCallback((signal:AbortSignal)=>getPreprojectReport(taskId,signal),[taskId]);
  const report=useResource(`${taskId}:${result.data?.reviewed_version_id || ''}`,enabled && Boolean(result.data),reportLoader);
  const samples=useResource(`${taskId}:${issue}:${offset}:${result.data?.reviewed_version_id || ''}`,enabled && Boolean(result.data),sampleLoader);
  const selectIssue=(value:string)=>{setOffset(0);setParams(current=>{const next=new URLSearchParams(current);value ? next.set('issue',value):next.delete('issue');return next;},{replace:true});};
  if (!taskId) return <Alert type="info" message="请先在任务监控页选择已完成的任务。" />;
  if (!enabled) return <Alert type="info" message="任务尚未完成或正在读取状态。" />;
  const stats=result.data?.statistics; const outcome=result.data?.outcome; const actions=outcome?.actions || stats?.action_counts;
  const count=(key:string)=> actions && typeof actions[key] === 'number' ? actions[key] as number : 'N/A';
  const sections=result.data?.quality.metrics || {};
  const cases: Array<[string,string,number|string]> = [['全部','',stats?.raw_sample_count ?? 'N/A'],['结构转换','structure_conversion',count('structure_conversion_records')],['字段规范化','cleaning_modified',count('field_normalization_records')],['精确重复','exact_duplicate',result.data?.issue_counts?.exact_duplicate ?? 0],['归一化重复','normalized_duplicate',result.data?.issue_counts?.normalized_duplicate ?? 0],['近重复','near_duplicate_requires_review',result.data?.issue_counts?.near_duplicate_requires_review ?? 0],['隐私命中','privacy_hit',result.data?.issue_counts?.privacy_hit ?? 0],['待复核','pending_review',stats?.review_count ?? 'N/A']];
  return <div className="space-y-4">
    <Card title="治理结果概览" extra={<Space><Button onClick={result.refresh}>刷新质量结果</Button><Button onClick={()=>go('versions')}>查看版本与交付</Button></Space>}>
      {result.loading && <Typography.Text type="secondary">正在加载质量结果…</Typography.Text>}{result.error && <Alert type="error" showIcon message="质量结果加载失败" action={<Button onClick={result.refresh}>重试质量结果</Button>} />}
      {stats && <><div className="governance-metrics"><Statistic title="输入记录" value={stats.raw_sample_count} /><Statistic title="合格候选" value={stats.final_retained_count} /><Statistic title="待复核" value={stats.review_count} /><Statistic title="隔离或剔除" value={stats.quarantine_count + stats.drop_count} /></div>
        <div aria-label="数据处理流转" className="governance-flow"><div><span>输入记录</span><strong>{stats.input_nonblank_lines}</strong></div><div><span>已解析</span><strong>{stats.raw_sample_count}</strong></div><div><span>合格候选</span><strong>{stats.final_retained_count}</strong></div></div>
        <Typography.Paragraph type="secondary">阶段吞吐、规则命中和互斥终态口径不同；各类处理动作可能重叠，不能相加。</Typography.Paragraph>
        <div className="governance-metrics">{[['结构转换',count('structure_conversion_records')],['字段规范化',count('field_normalization_records')],['内容语义修复','未执行'],['重复剔除',count('duplicate_removed_records')],['隐私处理',count('privacy_masked_records')],['人工复核',count('human_reviewed_records')]].map(([label,value])=><Statistic key={String(label)} title={label} value={value} />)}</div></>}
    </Card>
    {outcome && <Card title="最终质量认定"><Row gutter={[16,16]}>
      <Col xs={24} lg={8}><Card size="small" title="工程质量" extra={<Tag color={outcome.engineering.status==='passed'?'success':'warning'}>{outcome.engineering.status==='passed'?'规则通过':'待确认'}</Tag>}><p>{outcome.engineering.summary}</p><Typography.Text type="secondary">{outcome.engineering.scope}</Typography.Text></Card></Col>
      <Col xs={24} lg={8}><Card size="small" title="专业内容" extra={<Tag>未认证</Tag>}><p>{outcome.professional.summary}</p><Typography.Text type="secondary">已处理复核 {outcome.professional.manual_reviewed} 条；不等于专家认证。</Typography.Text></Card></Col>
      <Col xs={24} lg={8}><Card size="small" title="来源与发布" extra={<Tag color={outcome.publication.release_eligible?'success':'warning'}>{outcome.publication.release_eligible?'满足当前条件':'待核验'}</Tag>}><p>来源版本：{outcome.publication.revision_verified?'已核验':'未核验'} · 许可：{outcome.publication.license_verified?'已核验':'未核验'}</p>{outcome.publication.reasons.map((reason,i)=><Typography.Paragraph key={i} type="secondary">{reason}</Typography.Paragraph>)}</Card></Col>
    </Row></Card>}
    {stats?.stages && <Card title="规则执行与处理流转"><div className="governance-source-grid">{stats.stages.map(stage=><Card size="small" key={stage.stage}><Typography.Text strong>{({read_schema:'结构检查',normalize_clean:'清洗与标准化',deduplication:'去重',privacy_and_rescan:'隐私保护与复检',quality_admission:'五维质量评价',export:'结果交付'} as Record<string,string>)[stage.stage] || '处理阶段'}</Typography.Text><p>处理 {stage.processed_count} 条 · {stage.status==='completed'?'已完成':stage.status}</p><p>{stage.error_count ? `异常 ${stage.error_count} 条` : '本批次未发现该阶段异常。'}</p><Button size="small" onClick={()=>selectIssue(`stage:${stage.stage}`)}>查看阶段问题</Button></Card>)}</div></Card>}
    {stats && <Card title="样本准入分布"><div className="governance-metrics">{[['keep','合格候选'],['review','待人工复核'],['repair_pending','待修复'],['quarantine','隔离'],['drop','剔除']].map(([key,label])=><Statistic key={key} title={label} value={stats.status_counts?.[key] ?? 0} />)}</div></Card>}
    {result.data && <Card title="五维质量画像"><div className="metric-overview-grid">{Object.entries(labels).map(([dimension,label])=>{const primary=DIMENSION_PRIMARY[dimension]; const raw=sections[dimension]?.[primary]; const metric=metricValue(primary,raw); const info=METRIC_METADATA[primary]; return <Card key={dimension} size="small" className="metric-overview"><Typography.Title level={5}>{label}</Typography.Title><Typography.Text type="secondary">{info?.name || '质量指标'}</Typography.Text><div className="metric-primary">{metric ? formatMetric(primary,metric.value) : 'N/A'}</div><Typography.Text type="secondary">{metric?.value == null ? '暂无可靠评价依据' : info?.description}</Typography.Text><details><summary>查看详细指标</summary>{Object.entries(sections[dimension] || {}).map(([key,item])=>{const parsed=metricValue(key,item);return parsed ? <QualityMetricCard key={key} name={key} metric={parsed} onSample={id=>selectIssue(`sample:${id}`)} /> : null;})}</details></Card>;})}</div></Card>}
    <Card title="处理案例与前后对照"><Typography.Paragraph type="secondary">来源内容先标准化并脱敏；处理前后均不展示敏感原文。结构映射说明原始字段与规范字段的关系。</Typography.Paragraph><Space wrap>{cases.map(([label,key,n])=><Button key={key} type={issue===key?'primary':'default'} onClick={()=>selectIssue(key)}>{label} · {n}</Button>)}</Space>
      {samples.loading && <p>样本加载中…</p>}{samples.error && <Alert type="error" message="样本加载失败" action={<Button onClick={samples.refresh}>重试样本</Button>} />}
      {samples.data?.items.map(sample=><details key={sample.sample_id} className="sample-diff"><summary>{sample.sample_id} · {states[sample.status] || sample.status}</summary><p>处理方式：{sample.change_kind || '规则处理'} · 变化字段：{(sample.changed_fields || []).map(key=>fieldNames[key] || key).join('、') || '未发现可显示的内容变化'}</p><p>原始结构映射：{Object.entries(sample.source_mapping || {}).map(([key,value])=>`${fieldNames[key] || key} ← ${value}`).join('；') || '暂无映射信息'}</p><Row gutter={[16,16]}>{[['处理前（脱敏）',sample.before],['处理后（脱敏）',sample.after]].map(([title,value])=><Col key={String(title)} xs={24} md={12}><Card size="small" title={String(title)}>{Object.entries((value || {}) as Record<string,string>).filter(([,text])=>Boolean(text)).map(([key,text])=><p key={key} className="sample-text"><strong>{fieldNames[key] || key}：</strong>{text}</p>)}</Card></Col>)}</Row><p>已执行规则：{sample.cleaning_changes.length ? '字段规范化' : '未检测到字段内容修改'}；隐私变动以规则命中为准。</p>{sample.review_decision && <p>人工决策：{sample.review_decision} · 复检：{sample.review_recheck || '无记录'}</p>}</details>)}
      {samples.data && !samples.data.items.length && <p>本批次未发现该类案例。</p>}<Space><Button disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-10))}>上一页</Button><Typography.Text>{samples.data?.total ?? 'N/A'} 条</Typography.Text><Button disabled={!samples.data || offset+10>=samples.data.total} onClick={()=>setOffset(offset+10)}>下一页</Button></Space>
    </Card>
    <Card title="治理报告" extra={<Button onClick={()=>void downloadGovernanceReport(taskId)}>下载治理报告</Button>}>
      {report.loading && <p>报告加载中…</p>}{report.error && <Alert type="error" message="报告加载失败" action={<Button onClick={report.refresh}>重试报告</Button>} />}{report.data && <article className="report-markdown"><ReactMarkdown remarkPlugins={[remarkGfm]}>{report.data}</ReactMarkdown></article>}
    </Card>
  </div>;
}
