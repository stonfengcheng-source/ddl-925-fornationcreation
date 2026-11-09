import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Col, Row, Space, Statistic, Typography } from 'antd';
import request from '@/services/request';

export default function ProductStart() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [summary, setSummary] = useState<{asset_count: number; running_tasks: number; pending_reviews: number | null; qualified_versions: number; experiment_count: number | null; training_ready: boolean; recent_tasks: Array<{task_id: string; source_id: string; status: string; processed: number; total: number}>} | null>(null);
  useEffect(() => {
    let active = true;
    request.get('/preproject-data/overview').then((value) => { if (active) setSummary(value as unknown as NonNullable<typeof summary>); })
      .catch(() => { if (active) setError('数据建设概览暂不可用，请检查连接后重试。'); });
    return () => { active = false; };
  }, []);
  const steps = [
    ['选择数据', '/app/data-governance/sources'], ['数据治理', '/app/data-governance/pipelines'],
    ['质量评价', '/app/data-governance/quality'], ['版本交付', '/app/data-governance/versions'],
    ['训练实验', '/app/model-experiments'], ['效果分析', '/app/model-experiments'],
  ];
  return <section style={{marginBottom: 24}}>
    <Card title={<Typography.Title level={3} style={{margin: 0}}>开始使用数鉴</Typography.Title>}>
      <Typography.Paragraph type="secondary">选择数据，配置治理规则，生成可追溯的数据版本并开展训练实验。</Typography.Paragraph>
      <Space wrap><Button type="primary" size="large" onClick={() => navigate('/app/data-governance/sources')}>新建数据治理任务</Button>
        <Button onClick={() => navigate('/app/model-experiments')}>新建训练实验</Button>
        <Button onClick={() => navigate('/app/data-assets')}>查看我的数据资产</Button>
        <Button onClick={() => navigate('/app/data-governance/sources')}>导入新数据</Button></Space>
      <Typography.Paragraph type="secondary" style={{marginTop: 10}}>内置数据已标明来源；正式数据仍需独立核验授权。</Typography.Paragraph>
      {error && <Alert type="warning" showIcon message={error} />}
      <Row gutter={[12,12]} style={{marginTop: 8}}>
        <Col xs={12} md={4}><Statistic title="数据资产" value={summary?.asset_count ?? '—'} /></Col>
        <Col xs={12} md={4}><Statistic title="运行中的治理任务" value={summary?.running_tasks ?? '—'} /></Col>
        <Col xs={12} md={4}><Statistic title="待人工复核" value={summary?.pending_reviews ?? '—'} /></Col>
        <Col xs={12} md={4}><Statistic title="合格候选版本" value={summary?.qualified_versions ?? '—'} /></Col>
        <Col xs={12} md={4}><Statistic title="训练实验" value={summary?.experiment_count ?? '—'} /></Col>
        <Col xs={12} md={4}><Typography.Text type="secondary">训练资源</Typography.Text><div>{summary ? summary.training_ready ? '已就绪' : '训练能力待配置' : '正在读取'}</div></Col>
      </Row>
    </Card>
    <Row gutter={[12,12]} style={{marginTop: 12}}>{steps.map(([label, href], index) => <Col key={label} xs={12} md={8} xl={4}><Card size="small" hoverable onClick={() => navigate(href)}><Typography.Text type="secondary">0{index + 1}</Typography.Text><div>{label} →</div></Card></Col>)}</Row>
    <Card title="最近数据治理任务" style={{marginTop: 12}} extra={<Button type="link" onClick={() => navigate('/app/data-governance/tasks')}>查看全部</Button>}>
      {summary?.recent_tasks.length ? summary.recent_tasks.map(task => <p key={task.task_id}><Button type="link" onClick={() => navigate(`/app/data-governance/tasks?source_id=${encodeURIComponent(task.source_id)}&task_id=${encodeURIComponent(task.task_id)}`)}>{task.status} · {task.processed}/{task.total} 条</Button></p>) : <Typography.Text type="secondary">{summary ? '还没有治理任务，可先创建示例任务。' : '正在读取任务。'}</Typography.Text>}
    </Card>
  </section>;
}
