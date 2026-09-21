import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import request from '@/services/request';
import {
  Layout,
  Row,
  Col,
  Spin,
  Button,
  Breadcrumb,
  Card as AntCard,
  Table,
  Tag,
  Statistic,
  Progress,
  Space,
  Descriptions,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  WalletOutlined,
  TeamOutlined,
  PieChartOutlined,
  CheckCircleOutlined,
  DollarOutlined,
} from '@ant-design/icons';

const { Content } = Layout;

interface ContributionItem {
  id: string;
  node_id: string;
  node_name: string;
  user_id: string;
  username: string;
  data_quality_score: number;
  data_quantity_score: number;
  computation_score: number;
  timeliness_score: number;
  overall_score: number;
  share_percentage: number;
  reward_amount: number;
  reward_currency: string;
  settlement_status: string;
}

interface ContribData {
  task_id: string;
  task_name: string;
  reward_pool: number;
  reward_currency: string;
  status: string;
  contributions: ContributionItem[];
}

const SettlementTag = ({ status }: { status: string }) => {
  const m: Record<string, { color: string; text: string }> = {
    pending: { color: 'warning', text: '待结算' },
    settled: { color: 'success', text: '已结算' },
  };
  const cfg = m[status] || m.pending;
  return <Tag color={cfg.color}>{cfg.text}</Tag>;
};

const RevenueShare: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<ContribData | null>(null);
  const [settling, setSettling] = useState(false);

  useEffect(() => {
    if (!taskId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    request
      .get(`/training/${taskId}/contributions`)
      .then((res: any) => setData(res?.data || res || null))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [taskId]);

  const handleSettle = async () => {
    if (!taskId) return;
    setSettling(true);
    try {
      await request.post(`/training/${taskId}/settle`);
      message.success('结算完成！奖金已分配到各数据提供方钱包');
      // Refresh
      const res: any = await request.get(`/training/${taskId}/contributions`);
      setData(res?.data || res || null);
    } catch (error: any) {
      const detail = error?.response?.data?.detail || '结算失败';
      message.error(detail);
    } finally {
      setSettling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Spin size="large" />
          <span>加载贡献度数据...</span>
        </div>
      </div>
    );
  }

  if (!data) return <div className="p-8 text-center">暂无贡献度数据</div>;

  const totalReward = data.reward_pool || 0;
  const settledAmount = data.contributions
    .filter((c) => c.settlement_status === 'settled')
    .reduce((s, c) => s + c.reward_amount, 0);
  const pendingAmount = data.contributions
    .filter((c) => c.settlement_status === 'pending')
    .reduce((s, c) => s + c.reward_amount, 0);
  const allSettled = data.contributions.every((c) => c.settlement_status === 'settled');

  const columns = [
    {
      title: '排名',
      key: 'rank',
      width: 60,
      render: (_: any, __: any, index: number) => (
        <span className="font-bold text-lg" style={{ color: index === 0 ? '#ffd700' : index === 1 ? '#c0c0c0' : '#cd7f32' }}>
          #{index + 1}
        </span>
      ),
    },
    { title: '节点名称', dataIndex: 'node_name', key: 'node_name' },
    { title: '提供方', dataIndex: 'username', key: 'username' },
    {
      title: '数据质量',
      dataIndex: 'data_quality_score',
      key: 'data_quality_score',
      width: 120,
      render: (v: number) => <Progress percent={v} size="small" strokeColor="#52c41a" />,
    },
    {
      title: '数据量',
      dataIndex: 'data_quantity_score',
      key: 'data_quantity_score',
      width: 120,
      render: (v: number) => <Progress percent={v} size="small" strokeColor="#1890ff" />,
    },
    {
      title: '计算贡献',
      dataIndex: 'computation_score',
      key: 'computation_score',
      width: 120,
      render: (v: number) => <Progress percent={v} size="small" strokeColor="#722ed1" />,
    },
    {
      title: '综合占比',
      dataIndex: 'share_percentage',
      key: 'share_percentage',
      width: 100,
      render: (v: number) => <span className="font-bold text-blue-600">{v.toFixed(1)}%</span>,
    },
    {
      title: '应得奖励',
      dataIndex: 'reward_amount',
      key: 'reward_amount',
      width: 130,
      render: (v: number, r: ContributionItem) => (
        <span className="font-mono font-semibold text-green-600">
          ¥{v.toLocaleString()} {r.reward_currency}
        </span>
      ),
    },
    {
      title: '结算状态',
      dataIndex: 'settlement_status',
      key: 'settlement_status',
      width: 100,
      render: (s: string) => <SettlementTag status={s} />,
    },
  ];

  return (
    <Content>
      <div className="mb-6">
        <Breadcrumb
          items={[
            { title: '联邦学习' },
            { title: '训练任务' },
            { title: '贡献度与分账' },
          ]}
          className="mb-4"
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} type="text" />
            <div>
              <h1 className="text-2xl font-bold m-0">{data.task_name} — 贡献度分配</h1>
              <p className="text-gray-500 m-0 text-sm">
                ID: {data.task_id} | 状态: {data.status}
              </p>
            </div>
          </div>
          <Space>
            <Button onClick={() => navigate(`/app/federated/training/${taskId}`)}>
              返回训练监控
            </Button>
            {!allSettled && data.status === 'completed' && (
              <Button
                type="primary"
                icon={<DollarOutlined />}
                onClick={handleSettle}
                loading={settling}
              >
                确认结算
              </Button>
            )}
          </Space>
        </div>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="总奖励池"
              value={totalReward}
              prefix={<WalletOutlined />}
              suffix="CNY"
              valueStyle={{ color: '#1890ff' }}
            />
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="已分配"
              value={settledAmount}
              prefix={<CheckCircleOutlined />}
              suffix="CNY"
              valueStyle={{ color: '#52c41a' }}
            />
            <Progress
              percent={totalReward > 0 ? Math.round((settledAmount / totalReward) * 100) : 0}
              size="small"
              className="mt-2"
            />
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="待分配"
              value={pendingAmount}
              prefix={<DollarOutlined />}
              suffix="CNY"
              valueStyle={{ color: '#faad14' }}
            />
          </AntCard>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <AntCard>
            <Statistic
              title="参与节点"
              value={data.contributions.length}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
            <div className="text-gray-500 text-sm mt-2">
              {allSettled ? '✅ 全部已结算' : '⏳ 待结算'}
            </div>
          </AntCard>
        </Col>
      </Row>

      {/* 贡献度表格 */}
      <AntCard
        title={<Space><PieChartOutlined /><span>节点贡献度排名</span></Space>}
        className="mb-6"
      >
        <Table
          columns={columns}
          dataSource={data.contributions.sort((a, b) => b.share_percentage - a.share_percentage)}
          rowKey="id"
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      </AntCard>

      {/* 分账规则 */}
      <AntCard title="分账规则说明">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="计算方式">简化 Shapley 贡献度</Descriptions.Item>
          <Descriptions.Item label="数据量权重">40%</Descriptions.Item>
          <Descriptions.Item label="数据质量权重">30%</Descriptions.Item>
          <Descriptions.Item label="计算贡献权重">20%</Descriptions.Item>
          <Descriptions.Item label="时效性权重">10%</Descriptions.Item>
          <Descriptions.Item label="分配公式">节点奖励 = 奖励池 × (节点贡献度 / 总贡献度)</Descriptions.Item>
        </Descriptions>
      </AntCard>
    </Content>
  );
};

export default RevenueShare;
