import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import request from '@/services/request';
import {
  Breadcrumb,
  Button,
  Card,
  Empty,
  Progress,
  Space,
  Spin,
  Table,
  Tag,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  NodeIndexOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';

interface TrainingStatusData {
  task_id: string;
  task_name: string;
  status: string;
  mode?: string;
  current_round: number;
  total_rounds: number;
  accuracy: number;
  loss: number;
  participants: number;
  started_at: string;
  logs: string[];
  round_metrics: { round: number; loss: number; accuracy: number }[];
  nodes: { node_id: string; node_name: string; status: string; data_samples: string }[];
  ready_count?: number;
  min_nodes?: number;
  ready_users?: string[];
}

interface TrainingLog {
  key: string;
  text: string;
}

const statusTagConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待启动' },
  matching: { color: 'processing', icon: <SyncOutlined spin />, text: '等待节点' },
  training: { color: 'processing', icon: <SyncOutlined spin />, text: '训练中' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '训练中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  failed: { color: 'error', icon: <SafetyCertificateOutlined />, text: '需要处理' },
};

const TrainingMonitor: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TrainingStatusData | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [starting, setStarting] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!taskId) {
      setLoading(false);
      return;
    }
    try {
      const res: any = await request.get(`/training/${taskId}/status`);
      const payload = res?.data || res || null;
      setData(payload ? {
        ...payload,
        round_metrics: payload.round_metrics || [],
        nodes: payload.nodes || [],
        logs: payload.logs || [],
      } : null);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    void fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!autoRefresh || !taskId) return undefined;
    const interval = window.setInterval(() => void fetchStatus(), 5000);
    return () => window.clearInterval(interval);
  }, [autoRefresh, fetchStatus, taskId]);

  const handleStartTraining = async () => {
    if (!taskId) return;
    setStarting(true);
    try {
      await request.post(`/training/${taskId}/start?mode=demo`);
      message.success('训练已启动，正在准备两个模拟节点');
      await fetchStatus();
    } catch (error: any) {
      message.error(error?.response?.data?.detail || '启动训练失败，请先确认节点已就绪');
    } finally {
      setStarting(false);
    }
  };

  const nodeColumns: ColumnsType<TrainingStatusData['nodes'][number]> = [
    { title: '节点名称', dataIndex: 'node_name', key: 'node_name' },
    {
      title: '连接状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={status === 'training' || status === 'accepted' ? 'blue' : status === 'completed' ? 'green' : 'default'}>{status === 'accepted' ? '已接入' : status === 'training' ? '训练中' : status === 'completed' ? '已完成' : status || '等待中'}</Tag>,
    },
    { title: '本地样本', dataIndex: 'data_samples', key: 'data_samples' },
  ];

  const metricColumns: ColumnsType<TrainingStatusData['round_metrics'][number]> = [
    { title: '轮次', dataIndex: 'round', key: 'round', width: 80 },
    { title: 'Loss', dataIndex: 'loss', key: 'loss', render: (value: number) => value.toFixed(4) },
    { title: '准确率', dataIndex: 'accuracy', key: 'accuracy', render: (value: number) => `${(value * 100).toFixed(2)}%` },
  ];

  const normalizedLogs = useMemo<TrainingLog[]>(() => {
    if (!data?.logs?.length) return [];
    return data.logs.slice(-8).reverse().map((text, index) => ({ key: `${index}-${text}`, text }));
  }, [data?.logs]);

  if (loading) {
    return <div className="flex min-h-[420px] flex-col items-center justify-center gap-3 text-text-secondary"><Spin size="large" /><span>正在读取训练状态...</span></div>;
  }

  if (!data) {
    return <Empty className="py-20" description="任务不存在或无训练数据"><Button onClick={() => navigate('/app/my-tasks')}>返回我的任务</Button></Empty>;
  }

  const totalRounds = data.total_rounds || 1;
  const roundPercent = Math.min(100, Math.round(((data.current_round || 0) / totalRounds) * 100));
  const readyCount = data.ready_count || 0;
  const minNodes = data.min_nodes || 2;
  const readyPercent = Math.min(100, Math.round((readyCount / minNodes) * 100));
  const remotePending = (data.status === 'pending' || data.status === 'matching') && data.mode === 'remote';
  const demoPending = (data.status === 'pending' || data.status === 'matching') && !remotePending;
  const canStart = !remotePending || readyCount >= minNodes;
  const statusConfig = statusTagConfig[data.status] || statusTagConfig.pending;

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <Breadcrumb items={[{ title: '联邦学习' }, { title: '训练监控' }]} />

      <section className="rounded-2xl border border-[#dce9ff] bg-gradient-to-br from-[#e7f1ff] via-[#f5f9ff] to-white px-6 py-7 shadow-[0_16px_36px_rgba(30,111,255,0.08)] sm:px-8">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <button type="button" onClick={() => navigate('/app/federated')} className="mb-4 inline-flex items-center gap-2 border-0 bg-transparent p-0 text-sm text-[#1e6fff] hover:text-[#1557c0]"><ArrowLeftOutlined />返回联邦学习</button>
            <div className="mb-3 flex flex-wrap items-center gap-3"><Tag icon={statusConfig.icon} color={statusConfig.color}>{statusConfig.text}</Tag><span className="text-xs text-text-tertiary">任务 ID：{data.task_id}</span></div>
            <h1 className="m-0 text-3xl font-bold tracking-tight text-[#172033]">{data.task_name}</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-text-secondary">查看训练进度、指标和节点状态。</p>
          </div>
          <Space wrap>
            <Button icon={<ReloadOutlined />} onClick={() => void fetchStatus()}>刷新状态</Button>
            <Button icon={<SyncOutlined spin={autoRefresh} />} onClick={() => setAutoRefresh((value) => !value)}>{autoRefresh ? '自动刷新中' : '开启自动刷新'}</Button>
            {(data.status === 'pending' || data.status === 'matching') && <Button type="primary" icon={<ThunderboltOutlined />} loading={starting} disabled={!canStart} onClick={handleStartTraining}>{remotePending ? (canStart ? '启动远程训练' : `等待节点 ${readyCount}/${minNodes}`) : '启动本机演示'}</Button>}
          </Space>
        </div>
      </section>

      {demoPending && (
        <div className="flex flex-col gap-3 rounded-2xl border border-[#dce9ff] bg-[#f7fbff] px-5 py-4 text-sm md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <ThunderboltOutlined className="text-[#1e6fff]" />
            <div><div className="font-semibold text-[#172033]">本机演示</div><div className="mt-1 text-xs text-text-secondary">自动创建两个模拟节点，无需额外配置。</div></div>
          </div>
          <Tag color="success">可启动</Tag>
        </div>
      )}

      {remotePending && (
        <Card className="rounded-2xl" bordered={false} title={<div className="flex items-center gap-2"><TeamOutlined className="text-[#1e6fff]" /><span>第一步：确认参与节点</span></div>} extra={<Tag color={canStart ? 'success' : 'warning'}>{canStart ? '可以启动' : '还差一些节点'}</Tag>}>
          <div className="flex flex-col gap-5 md:flex-row md:items-center">
            <Progress type="circle" percent={readyPercent} size={92} format={() => `${readyCount}/${minNodes}`} />
            <div className="min-w-0 flex-1">
              <h3 className="m-0 text-base font-semibold text-[#172033]">节点就绪后，训练才能开始</h3>
              <p className="mb-3 mt-2 text-sm leading-6 text-text-secondary">请让参与方在本地客户端上线。平台只接收训练参数，不会读取或上传原始数据。</p>
              {data.ready_users?.length ? <Space wrap>{data.ready_users.map((name) => <Tag key={name} icon={<CheckCircleOutlined />} color="green">{name}</Tag>)}</Space> : <span className="text-xs text-text-tertiary">暂时没有客户端报告就绪</span>}
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <MetricTile icon={<NodeIndexOutlined />} label="训练进度" value={`${roundPercent}%`} hint={`第 ${data.current_round || 0}/${data.total_rounds || 0} 轮`} tone="blue" />
        <MetricTile icon={<SafetyCertificateOutlined />} label="当前准确率" value={`${((data.accuracy || 0) * 100).toFixed(2)}%`} hint={data.status === 'completed' ? '最终结果' : '实时更新'} tone="green" />
        <MetricTile icon={<ThunderboltOutlined />} label="当前损失" value={data.loss > 100 ? '-' : (data.loss || 0).toFixed(4)} hint="Loss 值" tone="orange" />
        <MetricTile icon={<DatabaseOutlined />} label="参与节点" value={data.participants || data.nodes.length} hint="已接入训练的节点" tone="purple" />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Card className="rounded-2xl" title={<div className="flex items-center gap-2"><SafetyCertificateOutlined className="text-[#1e6fff]" /><span>训练进度</span><span className="text-xs font-normal text-text-tertiary">每 5 秒自动更新</span></div>}>
          <Progress percent={roundPercent} strokeColor="#1e6fff" trailColor="#eaf2ff" />
          {data.round_metrics.length ? <Table className="mt-4" size="small" columns={metricColumns} dataSource={data.round_metrics.slice(-8).reverse()} rowKey="round" pagination={false} /> : <Empty className="py-8" image={Empty.PRESENTED_IMAGE_SIMPLE} description="训练开始后，这里会显示每轮指标" />}
        </Card>

        <Card className="rounded-2xl" title={<div className="flex items-center gap-2"><SyncOutlined className="text-[#1e6fff]" /><span>最近动态</span></div>}>
          {normalizedLogs.length ? <div className="space-y-3">{normalizedLogs.map((log) => <div key={log.key} className="flex gap-3 text-sm leading-6 text-text-secondary"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#1e6fff]" /><span>{log.text}</span></div>)}</div> : <Empty className="py-8" image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无训练日志" />}
        </Card>
      </div>

      <Card className="rounded-2xl" title={<div className="flex items-center gap-2"><TeamOutlined className="text-[#1e6fff]" /><span>参与节点</span><span className="text-xs font-normal text-text-tertiary">只展示连接状态和样本规模</span></div>}>
        {data.nodes.length ? <Table size="small" columns={nodeColumns} dataSource={data.nodes} rowKey="node_id" pagination={false} scroll={{ x: 520 }} /> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无节点信息" />}
      </Card>
    </div>
  );
};

const MetricTile: React.FC<{ icon: React.ReactNode; label: string; value: string | number; hint: string; tone: 'blue' | 'green' | 'orange' | 'purple' }> = ({ icon, label, value, hint, tone }) => {
  const toneClasses = {
    blue: 'bg-[#eaf2ff] text-[#1e6fff]',
    green: 'bg-[#e8f7f0] text-[#159570]',
    orange: 'bg-[#fff3e2] text-[#e88918]',
    purple: 'bg-[#f0ebff] text-[#7357d9]',
  };
  return <div className="rounded-2xl border border-border-light bg-white p-4 shadow-[0_4px_14px_rgba(23,32,51,0.04)]"><div className={`mb-3 flex h-9 w-9 items-center justify-center rounded-xl ${toneClasses[tone]}`}>{icon}</div><div className="text-xs text-text-secondary">{label}</div><div className="mt-1 text-xl font-bold tracking-tight text-[#172033]">{value}</div><div className="mt-1 truncate text-[11px] text-text-tertiary">{hint}</div></div>;
};

export default TrainingMonitor;
