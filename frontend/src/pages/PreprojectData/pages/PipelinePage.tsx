import * as React from 'react';
import { Button, Card, Collapse, Select, Space, Typography } from 'antd';
import { createPreprojectTask } from '@/services/api/preprojectData';
import { useWorkspace } from '../layout/PreprojectLayout';

export function PipelinePage() {
  const { sourceId, sources, go } = useWorkspace();
  const [clean, setClean] = React.useState(() => sessionStorage.getItem('pp-clean') !== 'false');
  const [near, setNear] = React.useState(() => sessionStorage.getItem('pp-near') !== 'false');
  const [distance, setDistance] = React.useState(() => Number(sessionStorage.getItem('pp-distance') ?? 3));
  const [name, setName] = React.useState(() => sessionStorage.getItem('pp-version') || '教育问答治理');
  const [template, setTemplate] = React.useState<'education_qa' | 'general_text'>('education_qa');
  const [busy, setBusy] = React.useState(false); const [error, setError] = React.useState('');
  const selected = sources.find(item => item.source_id === sourceId);
  const validated = Boolean(sourceId && (sessionStorage.getItem('pp-validated-source') === sourceId || ((selected?.is_platform_default || selected?.is_classification_dataset) && selected.default_ready)));
  React.useEffect(() => { sessionStorage.setItem('pp-clean', String(clean)); sessionStorage.setItem('pp-near', String(near)); sessionStorage.setItem('pp-distance', String(distance)); sessionStorage.setItem('pp-version', name); }, [clean, near, distance, name]);
  const submit = async () => { if (!validated || !name.trim() || !Number.isInteger(distance) || distance < 0 || distance > 64) { setError('请先验证数据，并填写有效的版本及阈值。'); return; } setBusy(true); setError(''); try { const result = await createPreprojectTask({ source_id: sourceId, template_id: template, cleaning_enabled: clean, near_duplicate_enabled: near, near_duplicate_hamming_distance: distance, near_duplicate_action: 'review_only', privacy_enabled: true, version_name: name }); go('tasks', { task_id: result.task.task_id, source_id: sourceId }); } catch { setError('任务创建失败，请核验数据源后重试。'); } finally { setBusy(false); } };
  return <Card><h2 className="text-lg font-semibold">处理配置</h2><Typography.Paragraph type="secondary">当前数据：{selected?.dataset_id || '未选择'} · 预计处理 {selected?.sample_count ?? 'N/A'} 条</Typography.Paragraph>
    <Space wrap><Typography.Text>治理模板</Typography.Text><Select aria-label="治理模板" value={template} onChange={(value) => setTemplate(value)} options={[{value:'education_qa',label:'教育问答标准治理'},{value:'general_text',label:'通用文本治理'}]} style={{minWidth:220}} /></Space>
    <div className="governance-source-grid" style={{margin:'20px 0'}}>{[['结构检查',true],['基础清洗',clean],['重复检测',true],['隐私保护',true],['五维质量评价',true]].map(([label,enabled]) => <Card key={String(label)} size="small"><Typography.Text strong>{label}</Typography.Text><p>{enabled ? '已启用' : '已关闭'}</p></Card>)}</div>
    <Collapse items={[{key:'advanced', label:'查看高级配置', children:<div className="space-y-3"><label><input type="checkbox" checked={clean} onChange={(e) => setClean(e.target.checked)} /> 执行格式清洗</label><br /><label><input type="checkbox" checked={near} onChange={(e) => setNear(e.target.checked)} /> 检测近重复</label><label className="block">近重复阈值 <input aria-label="近重复阈值" type="number" min="0" max="64" value={distance} onChange={(e) => setDistance(Number(e.target.value))} className="w-20 rounded border p-1" /></label><label className="block">输出版本名称 <input aria-label="输出版本名称" value={name} onChange={(e) => setName(e.target.value)} className="rounded border p-2" /></label></div>}]} />
    <Typography.Paragraph type="secondary" style={{marginTop:16}}>近重复进入人工复核；来源许可未核验时仅形成候选，不自动发布。</Typography.Paragraph>{!validated && <p>请返回数据选择页面验证当前文件。</p>}{error && <p role="alert">{error}</p>}<Button type="primary" size="large" disabled={!validated} loading={busy} onClick={() => void submit()}>开始治理</Button></Card>;
}
