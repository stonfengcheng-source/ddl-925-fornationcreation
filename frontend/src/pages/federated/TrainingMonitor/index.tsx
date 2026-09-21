import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Layout,
  Row,
  Col,
  Spin,
  Button,
  Breadcrumb,
  Tag,
  Statistic,
  Progress,
  Table,
  Card as AntCard,
  Badge,
  Space,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  DashboardOutlined,
  TeamOutlined,
  DatabaseOutlined,
  TrophyOutlined,
  LineChartOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  DollarOutlined,
  PieChartOutlined,
} from '@ant-design/icons';

const { Content } = Layout;

interface TrainingStatusData {
  task_id: string;
  task_name: string;
  status: string;
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

const statusTagConfig: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  pending: { color: 'default', icon: <ClockCircleOutlined />, text: '待开始' },
  matching: { color: 'default', icon: <ClockCircleOutlined />, text: '匹配中' },
  training: { color: 'processing', icon: <SyncOutlined spin />, text: '训练中' },
  running: { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
  completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
  settled: { color: 'success', icon: <DollarOutlined />, text: '已结算' },
  failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
};

const TrainingMonitor: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<TrainingStatusData | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [starting, setStarting] = useState(false);
  const [settling, setSettling] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!taskId) {
      setLoading(false);
      return;
    }
    try {
      const res: any = await request.get(`/training/${taskId}/status`);
      setData(res?.data || res || null);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchStatus]);

  const handleStartTraining = async () => {
    if (!taskId) return;
    setStarting(true);
    try {
      await request.post(`/training/${taskId}/start?mode=remote`);
      message.success('联邦学习训练已启动！客户端将自动连接...');
      fetchStatus();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '启动训练失败';
      message.error(detail);
    } finally {
      setStarting(false);
    }
  };

  const handleDownloadModel = async () => {
    if (!taskId) return;
    try {
      const res = await request.get(`/training/${taskId}/model`, { responseType: 'blob' });
      const blob = new Blob([res as any]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `model_${taskId}.pt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      message.success('模型下载成功');
    } catch {
      message.error('模型下载失败');
    }
  };

  const handleSettle = async () => {
    if (!taskId) return;
    setSettling(true);
    try {
      await request.post(`/training/${taskId}/settle`);
      message.success('结算完成！奖金已分配到各数据提供方钱包');
      fetchStatus();
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '结算失败';
      message.error(detail);
    } finally {
      setSettling(false);
    }
  };

  const handleViewContributions = () => {
    if (!taskId) return;
    navigate(`/app/federated/revenue/${taskId}`);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Spin size="large" />
          <span>加载训练监控数据...</span>
        </div>
      </div>
    );
  }

  if (!data) return <div className="p-8 text-center">任务不存在或无训练数据</div>;

  const roundPercent = data.total_rounds > 0
    ? Math.round((data.current_round / data.total_rounds) * 100)
    : 0;

  const statusCfg = statusTagConfig[data.status] || statusTagConfig['pending'];

  const nodeColumns = [
    { title: '节点名称', dataIndex: 'node_name', key: 'node_name' },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (s: string) => {
        const m: Record<string, string> = { accepted: 'green', training: 'blue', completed: 'green', failed: 'red' };
        return <Badge color={m[s] || 'gray'} text={s} />;
      },
    },
    { title: '数据样本', dataIndex: 'data_samples', key: 'data_samples' },
  ];

  return (
    <Content>
      {/* 顶部导航 */}
      <div className="mb-6">
        <Breadcrumb
          items={[
            { title: '联邦学习' },
            { title: '训练任务' },
            { title: '训练监控' },
          ]}
          className="mb-4"
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} type="text" />
            <div>
              <h1 className="text-2xl font-bold m-0">{data.task_name}</h1>
              <p className="text-gray-500 m-0 text-sm">
                ID: {data.task_id}
                {data.started_at && ` | 开始时间: ${new Date(data.started_at).toLocaleString()}`}
              </p>
            </div>
            <Tag icon={statusCfg.icon} color={statusCfg.color}>{statusCfg.text}</Tag>
          </div>
          <Space>
            <Button
              icon={autoRefresh ? <SyncOutlined spin /> : <SyncOutlined />}
              onClick={() => setAutoRefresh(!autoRefresh)}
              type={autoRefresh ? 'primary' : 'default'}
            >
              {autoRefresh ? '自动刷新中' : '自动刷新'}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={fetchStatus}>刷新</Button>
            {(data.status === 'pending' || data.status === 'matching') && (
              <Button
                type="primary"
                icon={<PlayCircleOutlined />}
                onClick={handleStartTraining}
                loading={starting}
                disabled={(data.ready_count || 0) < (data.min_nodes || 2)}
              >
                启动训练 ({data.ready_count || 0}/{data.min_nodes || 2} 就绪)
              </Button>
            )}
          </Space>
        </div>
      </div>

      {/* 节点就绪状态（训练前显示） */}
      {(data.status === 'pending' || data.status === 'matching') && (
        <Row className="mb-6">
          <Col span={24}>
            <AntCard
              title={<Space><TeamOutlined /><span>客户端就绪状态</span></Space>}
              extra={<Tag color={(data.ready_count || 0) >= (data.min_nodes || 2) ? 'success' : 'warning'}>
                {(data.ready_count || 0) >= (data.min_nodes || 2) ? '✅ 全部就绪，可以启动训练' : `⏳ 等待客户端就绪 ${data.ready_count || 0}/${data.min_nodes || 2}`}
              </Tag>}
            >
              <div className="flex items-center gap-4">
                <Progress
                  type="circle"
                  percent={Math.round(((data.ready_count || 0) / (data.min_nodes || 2)) * 100)}
                  size={80}
                  format={() => `${data.ready_count || 0}/${data.min_nodes || 2}`}
                />
                <div>
                  <p className="text-gray-500 mb-2">已就绪的客户端节点：</p>
                  {(data.ready_users && data.ready_users.length > 0) ? (
                    <Space wrap>
                      {data.ready_users.map((u: string) => (
                        <Tag key={u} color="green" icon={<CheckCircleOutlined />}>{u}</Tag>
                      ))}
                    </Space>
                  ) : (
                    <span className="text-gray-400">暂无客户端就绪，请等待数据提供方在客户端中部署...</span>
                  )}
                </div>
              </div>
            </AntCard>
          </Col>
        </Row>
      )}

      {/* 核心指标 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="训练进度"
              value={roundPercent}
              suffix="%"
              prefix={<DashboardOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
            <div className="mt-2">
              <Progress percent={roundPercent} size="small" showInfo={false} />
              <div className="text-gray-500 text-sm mt-1">
                第 {data.current_round} / {data.total_rounds} 轮
              </div>
            </div>
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="当前准确率"
              value={((data.accuracy || 0) * 100).toFixed(2)}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
            <div className="text-gray-500 text-sm mt-2">
              {data.status === 'completed' ? '最终准确率' : '实时更新'}
            </div>
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="当前损失"
              value={data.loss > 100 ? '-' : data.loss.toFixed(4)}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
            <div className="text-gray-500 text-sm mt-2">
              {data.status === 'completed' ? '最终损失' : 'Loss 值'}
            </div>
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="参与节点"
              value={data.participants}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
            <div className="text-gray-500 text-sm mt-2">
              {data.nodes.length} 个节点已注册
            </div>
          </AntCard>
        </Col>
      </Row>

      {/* 轮次指标表格 */}
      {data.round_metrics.length > 0 && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col span={24}>
            <AntCard
              title={<Space><LineChartOutlined /><span>各轮训练指标</span></Space>}
            >
              <Table
                dataSource={data.round_metrics}
                rowKey="round"
                pagination={false}
                size="small"
                columns={[
                  { title: '轮次', dataIndex: 'round', key: 'round', render: (r: number) => `第 ${r} 轮` },
                  { title: 'Loss', dataIndex: 'loss', key: 'loss', render: (l: number) => l.toFixed(4) },
                  {
                    title: 'Accuracy',
                    dataIndex: 'accuracy',
                    key: 'accuracy',
                    render: (a: number) => (
                      <span>
                        {(a * 100).toFixed(2)}%
                        <Progress percent={a * 100} size="small" showInfo={false} style={{ width: 80, marginLeft: 8 }} />
                      </span>
                    ),
                  },
                ]}
              />
            </AntCard>
          </Col>
        </Row>
      )}

      {/* 训练完成后的操作按钮 */}
      {(data.status === 'completed' || data.status === 'settled') && (
        <Row gutter={[16, 16]} className="mb-6">
          <Col span={24}>
            <AntCard
              title={<Space><CheckCircleOutlined /><span>训练已完成 — 后续操作</span></Space>}
            >
              <Space size="large" wrap>
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  size="large"
                  onClick={handleDownloadModel}
                >
                  下载训练模型
                </Button>
                <Button
                  icon={<PieChartOutlined />}
                  size="large"
                  onClick={handleViewContributions}
                >
                  查看贡献度分配
                </Button>
                {data.status === 'completed' && (
                  <Button
                    type="primary"
                    danger
                    icon={<DollarOutlined />}
                    size="large"
                    onClick={handleSettle}
                    loading={settling}
                  >
                    确认结算（分配奖金）
                  </Button>
                )}
                {data.status === 'settled' && (
                  <Tag color="success" className="text-base px-4 py-1">
                    ✅ 已结算 — 奖金已分配到各提供方钱包
                  </Tag>
                )}
              </Space>
            </AntCard>
          </Col>
        </Row>
      )}

      {/* 节点列表和日志 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <AntCard
            title={<Space><DatabaseOutlined /><span>参与节点</span></Space>}
          >
            <Table
              columns={nodeColumns}
              dataSource={data.nodes}
              rowKey="node_id"
              pagination={false}
              size="small"
            />
          </AntCard>
        </Col>
        <Col xs={24} lg={12}>
          <AntCard
            title={<Space><SyncOutlined /><span>训练日志</span></Space>}
          >
            <div
              className="bg-gray-900 text-green-400 p-4 rounded font-mono text-xs overflow-y-auto"
              style={{ maxHeight: 400 }}
            >
              {data.logs.length > 0 ? (
                data.logs.map((line, i) => (
                  <div key={i} className="mb-1">{line}</div>
                ))
              ) : (
                <div className="text-gray-500">暂无日志</div>
              )}
            </div>
          </AntCard>
        </Col>
      </Row>
    </Content>
  );
};

export default TrainingMonitor;
