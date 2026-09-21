import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Layout,
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Button,
  Breadcrumb,
  Badge,
  Space,
  Tooltip,
  Alert,
  Tag,
  Spin,
} from 'antd';
import {
  SafetyOutlined,
  ArrowLeftOutlined,
  DownloadOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LineChartOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

// 类型导入
import type { NodePrivacyBudget, PrivacyBudgetConsumption, TaskPrivacyBudgetSummary } from '@/types/training';

// API 请求
import request from '@/services/request';

// 组件导入
import PrivacyBudgetCard from '@/components/privacy/PrivacyBudgetCard';
import PrivacyBudgetTrendChart from '@/components/privacy/PrivacyBudgetTrendChart';

const { Content } = Layout;

// 空状态默认值
const emptySummary: TaskPrivacyBudgetSummary = {
  taskId: '',
  epsilonTotal: 0,
  epsilonConsumed: 0,
  epsilonRemaining: 0,
  delta: 0,
  nodeBudgets: [],
  estimatedRoundsRemaining: 0,
  consumptionTrend: [],
};

const emptyGlobalStats = {
  totalTasks: 0,
  activeTasks: 0,
  totalEpsilonAllocated: 0,
  totalEpsilonConsumed: 0,
  totalEpsilonRemaining: 0,
  nodesWithWarning: 0,
  nodesExhausted: 0,
  avgConsumptionRate: 0,
  consumptionTrend: [] as any[],
};

/**
 * PrivacyBudgetDashboard 页面
 * 全局隐私预算仪表盘
 * 展示所有任务的隐私预算分配、消耗趋势和节点状态
 */
const PrivacyBudgetDashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<TaskPrivacyBudgetSummary>(emptySummary);
  const [globalStats, setGlobalStats] = useState(emptyGlobalStats);
  const [hasData, setHasData] = useState(false);

  // 从后端加载隐私预算数据
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        // 并行请求任务预算和全局统计
        const [summaryRes, globalRes] = await Promise.all([
          request.get('/training/privacy-budget/summary'),
          request.get('/training/privacy-budget/global'),
        ]);

        const summaryData = summaryRes.data?.data || summaryRes.data;
        const globalData = globalRes.data?.data || globalRes.data;

        // 如果后端返回了有效的DP任务数据
        if (summaryData && summaryData.dpEnabled && summaryData.taskId !== 'N/A') {
          setSummary({
            taskId: summaryData.taskId,
            epsilonTotal: summaryData.epsilonTotal,
            epsilonConsumed: summaryData.epsilonConsumed,
            epsilonRemaining: summaryData.epsilonRemaining,
            delta: summaryData.delta,
            nodeBudgets: summaryData.nodeBudgets || [],
            estimatedRoundsRemaining: summaryData.estimatedRoundsRemaining,
            consumptionTrend: summaryData.consumptionTrend || [],
          });
          setHasData(true);
        } else {
          setSummary(emptySummary);
          setHasData(false);
        }

        if (globalData) {
          setGlobalStats({
            totalTasks: globalData.totalTasks || 0,
            activeTasks: globalData.activeTasks || 0,
            totalEpsilonAllocated: globalData.totalEpsilonAllocated || 0,
            totalEpsilonConsumed: globalData.totalEpsilonConsumed || 0,
            totalEpsilonRemaining: globalData.totalEpsilonRemaining || 0,
            nodesWithWarning: summaryData?.nodeBudgets?.filter((n: any) => n.status === 'warning').length || 0,
            nodesExhausted: summaryData?.nodeBudgets?.filter((n: any) => n.status === 'exhausted').length || 0,
            avgConsumptionRate: globalData.avgConsumptionRate || 0,
            consumptionTrend: summaryData?.consumptionTrend || [],
          });
        }
      } catch (error) {
        console.warn('隐私预算API请求失败:', error);
        setSummary(emptySummary);
        setGlobalStats(emptyGlobalStats);
        setHasData(false);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // 节点表格列定义
  const nodeColumns: ColumnsType<NodePrivacyBudget> = [
    {
      title: '节点名称',
      dataIndex: 'nodeName',
      key: 'nodeName',
      render: (text, record) => (
        <Space>
          <span className="font-medium">{text}</span>
          <Tag color="blue">{record.nodeId}</Tag>
        </Space>
      ),
    },
    {
      title: '总预算 (ε)',
      dataIndex: 'epsilonTotal',
      key: 'epsilonTotal',
      align: 'right',
      render: (value) => <span className="font-mono">{value.toFixed(3)}</span>,
    },
    {
      title: '已消耗 (ε)',
      dataIndex: 'epsilonConsumed',
      key: 'epsilonConsumed',
      align: 'right',
      render: (value) => <span className="font-mono">{value.toFixed(3)}</span>,
    },
    {
      title: '剩余 (ε)',
      dataIndex: 'epsilonRemaining',
      key: 'epsilonRemaining',
      align: 'right',
      render: (value, record) => (
        <span
          className="font-mono"
          style={{
            color:
              record.status === 'exhausted'
                ? '#f5222d'
                : record.status === 'warning'
                  ? '#fa8c16'
                  : '#52c41a',
          }}
        >
          {value.toFixed(3)}
        </span>
      ),
    },
    {
      title: '消耗率',
      key: 'consumptionRate',
      align: 'right',
      render: (_, record) => {
        const rate = (record.epsilonConsumed / record.epsilonTotal) * 100;
        return (
          <Tooltip title={`${rate.toFixed(1)}%`}>
            <span
              className="font-mono"
              style={{
                color:
                  rate >= 100
                    ? '#f5222d'
                    : rate >= 80
                      ? '#fa8c16'
                      : '#52c41a',
              }}
            >
              {rate.toFixed(1)}%
            </span>
          </Tooltip>
        );
      },
    },
    {
      title: 'Delta (δ)',
      dataIndex: 'delta',
      key: 'delta',
      align: 'right',
      render: (value) => (
        <span className="font-mono">{value.toExponential(2)}</span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      align: 'center',
      render: (status: 'safe' | 'warning' | 'exhausted') => {
        const config = {
          safe: {
            color: 'success',
            icon: <CheckCircleOutlined />,
            text: '安全',
          },
          warning: {
            color: 'warning',
            icon: <WarningOutlined />,
            text: '警告',
          },
          exhausted: {
            color: 'error',
            icon: <CloseCircleOutlined />,
            text: '已耗尽',
          },
        };
        const { color, icon, text } = config[status];
        return (
          <Badge
            status={color as any}
            text={
              <Space>
                {icon}
                {text}
              </Space>
            }
          />
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      align: 'center',
      render: (_, record) => (
        <Button type="link" size="small" onClick={() => navigate(`/app/edge-nodes/${record.nodeId}`)}>
          查看详情
        </Button>
      ),
    },
  ];

  // 消费趋势表格列
  const trendColumns: ColumnsType<PrivacyBudgetConsumption> = [
    {
      title: '轮次',
      dataIndex: 'round',
      key: 'round',
      width: 80,
      render: (round) => `第 ${round} 轮`,
    },
    {
      title: '本轮消耗 (ε)',
      dataIndex: 'epsilonConsumed',
      key: 'epsilonConsumed',
      align: 'right',
      render: (value) => <span className="font-mono">{value.toFixed(4)}</span>,
    },
    {
      title: '累计消耗 (ε)',
      dataIndex: 'epsilonCumulative',
      key: 'epsilonCumulative',
      align: 'right',
      render: (value) => (
        <span className="font-mono" style={{ color: '#fa8c16', fontWeight: 500 }}>
          {value.toFixed(4)}
        </span>
      ),
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp) => new Date(timestamp).toLocaleString(),
    },
  ];

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen bg-gray-50">
        <Spin size="large" tip="加载隐私预算数据..." />
      </div>
    );
  }

  const consumptionRate = summary.epsilonTotal > 0 ? (summary.epsilonConsumed / summary.epsilonTotal) * 100 : 0;
  const totalRounds = summary.consumptionTrend.length || 1;
  const avgConsumptionPerRound = summary.epsilonConsumed / totalRounds;

  return (
    <Content>
      {/* 顶部导航 */}
      <div className="mb-6">
        <Breadcrumb
          items={[
            { title: '联邦学习' },
            { title: '隐私预算' },
          ]}
          className="mb-4"
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)} type="text" />
            <div>
              <h1 className="text-2xl font-bold m-0 flex items-center gap-2">
                <SafetyOutlined className="text-orange-500" />
                隐私预算中心
              </h1>
              <p className="text-gray-500 m-0 text-sm">
                任务: {summary.taskId} | 实时监控各节点隐私预算消耗情况
              </p>
            </div>
          </div>
          <Space>
            <Button icon={<DownloadOutlined />}>导出报告</Button>
            <Button type="primary" icon={<LineChartOutlined />}>
              查看详细分析
            </Button>
          </Space>
        </div>
      </div>

      {/* 无数据提示 */}
      {!hasData && (
        <Alert
          message="暂无隐私预算数据"
          description="当前没有启用差分隐私的训练任务。发布启用DP的任务并开始训练后，此页面将展示真实的隐私预算消耗数据。"
          type="info"
          showIcon
          className="mb-6"
        />
      )}

      {/* 警告提示 */}
      {summary.nodeBudgets.some((n) => n.status === 'warning' || n.status === 'exhausted') && (
        <Alert
          message="隐私预算警告"
          description={
            <span>
              检测到 {summary.nodeBudgets.filter((n) => n.status === 'warning').length} 个节点预算即将耗尽，
              {summary.nodeBudgets.filter((n) => n.status === 'exhausted').length} 个节点预算已耗尽。
              请及时调整训练参数或增加隐私预算。
            </span>
          }
          type="warning"
          showIcon
          className="mb-6"
        />
      )}

      {/* 统计卡片行 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总预算"
              value={summary.epsilonTotal}
              precision={3}
              prefix={<SafetyOutlined />}
              valueStyle={{ color: '#262626' }}
              suffix="ε"
            />
            <div className="text-gray-500 text-sm mt-2">
              分配到 {summary.nodeBudgets.length} 个节点
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="已消耗"
              value={summary.epsilonConsumed}
              precision={3}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#fa8c16' }}
              suffix="ε"
            />
            <div className="text-orange-500 text-sm mt-2">
              消耗率: {consumptionRate.toFixed(1)}%
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="剩余预算"
              value={summary.epsilonRemaining}
              precision={3}
              prefix={<CheckCircleOutlined />}
              valueStyle={{
                color: summary.epsilonRemaining < summary.epsilonTotal * 0.2 ? '#f5222d' : '#52c41a',
              }}
              suffix="ε"
            />
            <div className="text-gray-500 text-sm mt-2">
              预计还可训练 {summary.estimatedRoundsRemaining} 轮
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均每轮消耗"
              value={avgConsumptionPerRound}
              precision={4}
              prefix={<LineChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
              suffix="ε/轮"
            />
            <div className="text-gray-500 text-sm mt-2">
              Delta (δ): {summary.delta.toExponential(2)}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 预算消耗趋势图 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col span={24}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>预算消耗趋势</span>
              </Space>
            }
            extra={
              <Space>
                <Tag color="orange">总预算: ε = {summary.epsilonTotal}</Tag>
                <Tag color="blue">当前: 第{totalRounds}轮</Tag>
              </Space>
            }
          >
            <PrivacyBudgetTrendChart
              data={summary.consumptionTrend}
              totalBudget={summary.epsilonTotal}
              height={350}
              title=""
            />
          </Card>
        </Col>
      </Row>

      {/* 节点预算卡片 */}
      <Row gutter={[16, 16]} className="mb-6">
        {summary.nodeBudgets.map((node) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={node.nodeId}>
            <PrivacyBudgetCard
              epsilon={node.epsilonTotal}
              epsilonConsumed={node.epsilonConsumed}
              delta={node.delta}
              nodeName={node.nodeName}
              size="medium"
              showProgress
              threshold={80}
            />
          </Col>
        ))}
      </Row>

      {/* 节点预算状态表格 */}
      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} lg={16}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                <span>各节点预算状态</span>
              </Space>
            }
          >
            <Table
              columns={nodeColumns}
              dataSource={summary.nodeBudgets}
              rowKey="nodeId"
              pagination={false}
              size="small"
              scroll={{ x: 'max-content' }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title={
              <Space>
                <LineChartOutlined />
                <span>最近消费记录</span>
              </Space>
            }
            className="h-full"
          >
            <Table
              columns={trendColumns}
              dataSource={summary.consumptionTrend.slice(-10).reverse()}
              rowKey="round"
              pagination={false}
              size="small"
              scroll={{ y: 400 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 全局统计信息 */}
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="平台全局隐私预算概览">
            <Row gutter={[16, 16]}>
              <Col xs={12} sm={6}>
                <Statistic title="总任务数" value={globalStats.totalTasks} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic title="活跃任务" value={globalStats.activeTasks} />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="警告节点"
                  value={globalStats.nodesWithWarning}
                  valueStyle={{ color: '#fa8c16' }}
                />
              </Col>
              <Col xs={12} sm={6}>
                <Statistic
                  title="已耗尽节点"
                  value={globalStats.nodesExhausted}
                  valueStyle={{ color: '#f5222d' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </Content>
  );
};

export default PrivacyBudgetDashboard;
