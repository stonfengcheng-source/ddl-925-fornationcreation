import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Alert, Button, Card, Col, Empty, InputNumber, Row, Select, Space, Statistic, Table, Tabs, Tag, Typography } from 'antd';
import { baselineEnvironment, baselineExperiments, baselineExperiment, baselineVersions, createBaselineExperiment, downloadBaselineExperiment, prepareDefaultBaseline } from '@/services/api/baseline';
import type { BaselineExperiment, BaselineVersion } from '@/services/api/baseline';
import AdvancedExperiment from './index';

const statusText: Record<BaselineExperiment['status'], string> = {pending:'等待中',running:'训练中',completed:'已完成',failed:'失败'};
export default function ExperimentsPage() {
  const [params] = useSearchParams();
  const [tab, setTab] = useState(params.get('data_version_id') ? 'new' : 'overview');
  const [version, setVersion] = useState(params.get('data_version_id') || '');
  const [versions, setVersions] = useState<BaselineVersion[]>([]);
  const [jobs, setJobs] = useState<BaselineExperiment[]>([]);
  const [selected, setSelected] = useState<BaselineExperiment | null>(null);
  const [environment, setEnvironment] = useState<{ready:boolean;message:string} | null>(null);
  const [seed, setSeed] = useState(42); const [testSize, setTestSize] = useState(.25);
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  const reload = useCallback(() => {
    baselineVersions().then(value => { setVersions(value.items); setVersion(current => current || value.items.find(item => item.compatible && item.is_default)?.version_id || ''); }).catch(() => setError('数据版本读取失败，请刷新后重试。'));
    baselineExperiments().then(value => setJobs(value.items)).catch(() => setError('实验历史读取失败，请刷新后重试。'));
    baselineEnvironment().then(setEnvironment).catch(() => setEnvironment({ready:false,message:'轻量训练资源检查失败。'}));
  }, []);
  useEffect(() => { reload(); }, [reload]);
  useEffect(() => {
    if (!selected || !['pending','running'].includes(selected.status)) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => baselineExperiment(selected.experiment_id, controller.signal).then(value => { setSelected(value); if (value.status === 'completed' || value.status === 'failed') reload(); }).catch(() => { if (!controller.signal.aborted) setError('实验状态读取失败，可刷新历史后重试。'); }), 1500);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [selected, reload]);
  const chosen = versions.find(item => item.version_id === version);
  async function start() {
    if (!chosen?.compatible || !environment?.ready) return;
    setBusy(true); setError('');
    try { const result = await createBaselineExperiment(version,seed,testSize); setSelected(result); setTab('history'); reload(); }
    catch { setError('实验启动失败，请确认数据标签、训练环境和参数后重试。'); }
    finally { setBusy(false); }
  }
  async function open(id:string) { try { setSelected(await baselineExperiment(id)); setTab('history'); } catch { setError('实验读取失败，请刷新后重试。'); } }
  async function prepare() { setBusy(true); setError(''); try { const result = await prepareDefaultBaseline(); setVersion(result.version_id); reload(); } catch { setError('基础训练数据准备失败，请检查治理任务及本机资源后重试。'); } finally { setBusy(false); } }
  return <main style={{maxWidth:1360,margin:'0 auto',padding:24}}>
    <Typography.Title level={2}>训练实验与效果验证</Typography.Title>
    <Typography.Paragraph type="secondary">基于治理后的数据版本开展可追溯的监督学习实验，或准备大模型微调。</Typography.Paragraph>
    {error && <Alert type="error" showIcon message={error} closable onClose={() => setError('')} style={{marginBottom:16}} />}
    <Tabs activeKey={tab} onChange={setTab} items={[
      {key:'overview',label:'实验概览',children:<Space direction="vertical" size="large" style={{width:'100%'}}>
        <Card><Row gutter={[16,16]}><Col xs={12} md={6}><Statistic title="训练实验" value={jobs.length} /></Col><Col xs={12} md={6}><Statistic title="已完成" value={jobs.filter(item => item.status === 'completed').length} /></Col><Col xs={12} md={6}><Statistic title="可用分类版本" value={versions.filter(item => item.compatible).length} /></Col><Col xs={12} md={6}><Typography.Text type="secondary">轻量训练</Typography.Text><div><Tag color={environment?.ready ? 'success' : 'default'}>{environment ? environment.ready ? '已就绪' : '待配置' : '检查中'}</Tag></div></Col></Row>
          <Button type="primary" size="large" style={{marginTop:24}} onClick={() => setTab('new')}>新建训练实验</Button></Card>
        <Card title="最近实验" extra={<Button type="link" onClick={() => setTab('history')}>查看全部</Button>}>{jobs.length ? jobs.slice(0,5).map(job => <p key={job.experiment_id}><Button type="link" onClick={() => void open(job.experiment_id)}>{job.dataset_id || '数据版本'} · {statusText[job.status]}</Button></p>) : <Empty description="尚无训练实验" />}</Card>
      </Space>},
      {key:'new',label:'新建实验',children:<Card title="配置轻量监督分类实验">
        <Alert type="info" showIcon message="TF-IDF + Logistic Regression 分类基线" description="真实执行训练与测试；结果仅用于监督分类基线，不代表大模型微调收益或 Proxy 排序。" style={{marginBottom:20}} />
        <Space direction="vertical" size="large" style={{width:'100%'}}>
          <div><Typography.Text strong>1 · 选择治理后的数据版本</Typography.Text><div><Select aria-label="训练数据版本" value={version || undefined} placeholder="选择带明确分类标签的候选版本" style={{width:'100%',maxWidth:650,marginTop:8}} options={versions.filter(item => item.compatible).map(item => ({value:item.version_id,label:`${item.dataset_id || '数据集'} · ${item.sample_count} 条${item.is_default ? ' · 平台基础版本' : ''}`}))} onChange={setVersion} /></div>
            {!versions.some(item => item.compatible) && <Typography.Paragraph type="secondary">暂无可训练版本。可准备平台基础训练数据，或<Link to="/app/data-governance/sources">前往数据治理</Link>。 <Button onClick={() => void prepare()} loading={busy}>准备基础训练数据</Button></Typography.Paragraph>}
            {chosen?.compatible && <Card size="small" style={{marginTop:12,maxWidth:650}}><Typography.Text>治理状态：{chosen.governance_status || '已完成'} · 样本：{chosen.sample_count} 条</Typography.Text><p>分类标签：{Object.entries(chosen.label_distribution || {}).map(([label,count]) => `${({mathematics:'数学',language:'语言',science:'科学'} as Record<string,string>)[label] || label} ${count} 条`).join(' · ') || '未提供分布'}</p></Card>}
            {versions.some(item => !item.compatible) && <details><summary>其他数据版本及不兼容原因</summary>{versions.filter(item => !item.compatible).map(item => <p key={item.version_id}>{item.dataset_id || '数据版本'} · {item.reason}</p>)}</details>}
            {chosen && !chosen.compatible && <Alert type="warning" showIcon message={chosen.reason} />}</div>
          <div><Typography.Text strong>2 · 训练方式</Typography.Text><p>Python 轻量基线 · TF-IDF 字符特征 + Logistic Regression</p><Typography.Text type="secondary">按类别分层划分训练集和测试集；重复文本会被拒绝，防止泄漏。</Typography.Text></div>
          <div><Typography.Text strong>3 · 默认参数</Typography.Text><div><Space wrap>随机种子 <InputNumber aria-label="随机种子" value={seed} min={0} max={2147483647} onChange={value => setSeed(value ?? 42)} /> 测试集比例 <InputNumber aria-label="测试集比例" min={.1} max={.4} step={.05} value={testSize} onChange={value => setTestSize(value ?? .25)} /></Space></div></div>
          <Typography.Text type="secondary">训练环境：{environment ? environment.ready ? '已就绪' : environment.message : '正在检查'}。 {!environment?.ready && <Link to="/app/resources">查看资源准备说明</Link>}</Typography.Text>
          <Button type="primary" size="large" loading={busy} disabled={!chosen?.compatible || !environment?.ready} onClick={() => void start()}>开始训练</Button>
        </Space></Card>},
      {key:'history',label:'实验记录与结果',children:<Row gutter={[16,16]}><Col xs={24} lg={8}><Card title="训练记录" extra={<Button onClick={reload}>刷新</Button>}>{jobs.length ? jobs.map(job => <p key={job.experiment_id}><Button type="link" onClick={() => void open(job.experiment_id)}>{job.dataset_id || '数据版本'} · {statusText[job.status]}</Button></p>) : <Empty description="暂无实验记录" />}</Card></Col><Col xs={24} lg={16}><Card title="实验结果">{!selected ? <Empty description="选择一条实验记录" /> : <Space direction="vertical" size="middle" style={{width:'100%'}}>
        <div><Tag color={selected.status === 'completed' ? 'success' : selected.status === 'failed' ? 'error' : 'processing'}>{statusText[selected.status]}</Tag>{selected.dataset_id} · {selected.sample_count} 条</div>
        <Typography.Text type="secondary">实验 ID：{selected.experiment_id} · TF-IDF + Logistic Regression · 数据版本 {selected.version_id} · 种子 {selected.seed} · 测试比例 {selected.test_size}</Typography.Text>
        {selected.error && <Alert type="error" showIcon message={selected.error} action={<Button onClick={() => setTab('new')}>修改配置后重试</Button>} />}
        {selected.metrics && <><Row gutter={[12,12]}><Col xs={12} md={6}><Statistic title="Accuracy" value={selected.metrics.accuracy} precision={4} /></Col><Col xs={12} md={6}><Statistic title="Macro-F1" value={selected.metrics.macro_f1} precision={4} /></Col><Col xs={12} md={6}><Statistic title="训练 / 测试" value={`${selected.metrics.train_count} / ${selected.metrics.test_count}`} /></Col><Col xs={12} md={6}><Statistic title="耗时（秒）" value={selected.metrics.duration_seconds} /></Col></Row>
          <Typography.Title level={5}>混淆矩阵</Typography.Title><Table size="small" pagination={false} rowKey="label" dataSource={selected.metrics.confusion_matrix.map((row,i) => ({label:selected.metrics!.classes[i], values:row}))} columns={[{title:'实际类别',dataIndex:'label'}, ...selected.metrics.classes.map((label,index) => ({title:`预测 ${label}`,render:(_:unknown,row:{values:number[]}) => row.values[index]}))]} />
          <Typography.Title level={5}>错误样本</Typography.Title>{selected.errors?.length ? <Table size="small" rowKey="sample_id" dataSource={selected.errors} pagination={{pageSize:5}} columns={[{title:'文本',dataIndex:'text'},{title:'实际',dataIndex:'actual'},{title:'预测',dataIndex:'predicted'}]} /> : <Typography.Text type="secondary">本次测试集中没有错误样本。</Typography.Text>}</>}
        {selected.logs?.length ? <details><summary>查看运行记录</summary>{selected.logs.map((line,i) => <p key={i}>{line}</p>)}</details> : null}
        <Space wrap>{selected.files.map(file => <Button key={file} onClick={() => downloadBaselineExperiment(selected.experiment_id,file).catch(() => setError('文件下载失败，请重试。'))}>下载 {file}</Button>)}</Space>
        </Space>}</Card></Col></Row>},
      {key:'advanced',label:'大模型微调与评测',children:<AdvancedExperiment />},
    ]} />
  </main>;
}
