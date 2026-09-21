/**
 * 预评估面板组件
 * 展示各Provider的预期贡献度分布
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Empty,
  Spin,
  Alert,
  Statistic,
  Row,
  Col,
  Tag,
  Tooltip,
  Progress,
} from 'antd';
import {
  PieChartOutlined,
  PlayCircleOutlined,
  InfoCircleOutlined,
  DatabaseOutlined,
  TrophyOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import { getPreEstimate, ProviderPreEstimate } from '@/services/api/preEstimate';

interface PreEstimatePanelProps {
  taskId: string;
  rewardPool: number;
  onStartTraining: () => void;
}

const PreEstimatePanel: React.FC<PreEstimatePanelProps> = ({
  taskId,
  rewardPool,
  onStartTraining,
}) => {
  const [loading, setLoading] = useState(false);
  const [providers, setProviders] = useState<ProviderPreEstimate[]>([]);
  const [error, setError] = useState<string | null>(null);

  // 获取预评估数据
  const fetchPreEstimate = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPreEstimate(taskId);
      setProviders(res.data?.providers || []);
    } catch (err: any) {
      console.error('获取预评估数据失败:', err);
      setError(err.message || '获取预评估数据失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPreEstimate();
  }, [taskId]);

  // 表格列定义
  const columns = [
    {
      title: 'Provider',
      dataIndex: 'provider_name',
      key: 'provider_name',
      render: (text: string, record: ProviderPreEstimate) => (
        <div>
          <div className="font-medium">{text}</div>
          <div className="text-xs text-gray-400">
            ID: {record.provider_id.substring(0, 8)}...
          </div>
        </div>
      ),
    },
    {
      title: (
        <span>
          <DatabaseOutlined /> 数据量
        </span>
      ),
      dataIndex: 'data_volume',
      key: 'data_volume',
      render: (value: number) => value.toLocaleString(),
      sorter: (a: ProviderPreEstimate, b: ProviderPreEstimate) =>
        a.data_volume - b.data_volume,
    },
    {
      title: '质量评分',
      dataIndex: 'quality_score',
      key: 'quality_score',
      render: (value: number) => (
        <Progress
          percent={Math.round(value * 100)}
          size="small"
          status={value >= 0.8 ? 'success' : value >= 0.6 ? 'normal' : 'exception'}
          format={(percent) => `${percent}%`}
        />
      ),
      sorter: (a: ProviderPreEstimate, b: ProviderPreEstimate) =>
        a.quality_score - b.quality_score,
    },
    {
      title: (
        <Tooltip title="基于数据量的多样性评估，使用对数函数降低大数据量的边际效益">
          <span>
            多样性 <InfoCircleOutlined className="text-gray-400" />
          </span>
        </Tooltip>
      ),
      dataIndex: 'diversity_score',
      key: 'diversity_score',
      render: (value: number) => (
        <Tag color={value >= 0.8 ? 'green' : value >= 0.5 ? 'blue' : 'orange'}>
          {(value * 100).toFixed(1)}%
        </Tag>
      ),
      sorter: (a: ProviderPreEstimate, b: ProviderPreEstimate) =>
        a.diversity_score - b.diversity_score,
    },
    {
      title: (
        <span className="flex items-center gap-1">
          <TrophyOutlined className="text-yellow-500" /> 预估贡献度
        </span>
      ),
      dataIndex: 'estimated_ratio',
      key: 'estimated_ratio',
      render: (value: number) => (
        <div className="flex items-center gap-2">
          <Progress
            percent={Math.round(value * 100)}
            size="small"
            strokeColor={
              value >= 0.3
                ? '#52c41a'
                : value >= 0.2
                  ? '#1890ff'
                  : value >= 0.1
                    ? '#faad14'
                    : '#ff4d4f'
            }
            style={{ width: 80 }}
          />
          <span className="font-medium text-blue-600">{(value * 100).toFixed(1)}%</span>
        </div>
      ),
      sorter: (a: ProviderPreEstimate, b: ProviderPreEstimate) =>
        a.estimated_ratio - b.estimated_ratio,
    },
    {
      title: '预估收益',
      dataIndex: 'estimated_amount',
      key: 'estimated_amount',
      render: (value: number) => (
        <span className="font-mono font-semibold text-orange-500">
          ¥{value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </span>
      ),
      sorter: (a: ProviderPreEstimate, b: ProviderPreEstimate) =>
        a.estimated_amount - b.estimated_amount,
    },
  ];

  // 饼图配置
  const pieOption = {
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        return `${params.name}: ${params.percent}%\n预估收益: ¥${params.value.toLocaleString()}`;
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: {
        color: '#333',
      },
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'center',
    },
    series: [
      {
        name: '预估贡献度',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        data: providers.map((p) => ({
          value: p.estimated_amount,
          name: p.provider_name,
        })),
      },
    ],
    color: ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2', '#eb2f96', '#f5222d'],
  };

  // 统计数据
  const totalProviders = providers.length;
  const totalDataVolume = providers.reduce((sum, p) => sum + p.data_volume, 0);
  const avgQualityScore =
    totalProviders > 0
      ? providers.reduce((sum, p) => sum + p.quality_score, 0) / totalProviders
      : 0;

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <Spin size="large" tip="计算预评估数据..." />
      </div>
    );
  }

  if (error) {
    return (
      <Empty
        description={
          <span>
            获取预评估数据失败
            <br />
            <small style={{ color: '#999' }}>{error}</small>
          </span>
        }
      >
        <Button type="primary" onClick={fetchPreEstimate}>
          重试
        </Button>
      </Empty>
    );
  }

  if (providers.length === 0) {
    return (
      <Empty
        description={
          <span>
            暂无已接受的Provider
            <br />
            <small style={{ color: '#999' }}>
              等待参与方接受任务邀请后，将显示预评估结果
            </small>
          </span>
        }
      >
        <Button type="primary" onClick={fetchPreEstimate} icon={<PieChartOutlined />}>
          刷新
        </Button>
      </Empty>
    );
  }

  return (
    <div className="space-y-6">
      {/* 提示信息 */}
      <Alert
        message="训练前数据价值预评估"
        description="以下预估基于各Provider已上传的数据统计特征（数据量、质量评分）计算，实际收益将根据训练完成后的真实贡献度进行结算。"
        type="info"
        showIcon
        icon={<PieChartOutlined />}
      />

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={<span className="flex items-center gap-1">
                <TeamOutlined /> 参与Provider
              </span>}
              value={totalProviders}
              suffix="个"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={<span className="flex items-center gap-1">
                <DatabaseOutlined /> 总数据量
              </span>}
              value={totalDataVolume}
              suffix="条"
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title={<span className="flex items-center gap-1">
                <TrophyOutlined /> 平均质量分
              </span>}
              value={avgQualityScore * 100}
              precision={1}
              suffix="%"
            />
          </Card>
        </Col>
      </Row>

      {/* 饼图和表格 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={10}>
          <Card
            title={<span className="flex items-center gap-2">
              <PieChartOutlined /> 预估贡献度分布
            </span>}
            className="h-full"
          >
            <ReactECharts
              option={pieOption}
              style={{ height: '350px', width: '100%' }}
              opts={{ renderer: 'canvas' }}
              notMerge={true}
            />
            <div className="text-center mt-4 pt-4 border-t border-gray-100">
              <div className="text-sm text-gray-500">奖励池总额</div>
              <div className="text-xl font-semibold text-orange-500">
                ¥{rewardPool.toLocaleString()}
              </div>
            </div>
          </Card>
        </Col>

        <Col xs={24} lg={14}>
          <Card
            title={<span className="flex items-center gap-2">
              <TeamOutlined /> Provider详情
            </span>}
            className="h-full"
          >
            <Table
              columns={columns}
              dataSource={providers}
              rowKey="provider_id"
              pagination={false}
              size="small"
              scroll={{ y: 350 }}
            />
          </Card>
        </Col>
      </Row>

      {/* 操作按钮 */}
      <div className="flex justify-center pt-4">
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={onStartTraining}
          className="min-w-[200px]"
        >
          确认启动训练
        </Button>
      </div>
    </div>
  );
};

export default PreEstimatePanel;
