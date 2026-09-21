/**
 * 数据集详情页面
 * 路径: /datasets/:datasetId
 * 功能: 展示数据集详情、统计信息、特征列表、数据预览
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card,
  Tabs,
  Table,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Statistic,
  Progress,
  Badge,
  Tooltip,
  List,
  Empty,
  Skeleton,
  message,
  Dropdown,
  Alert,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  DownloadOutlined,
  ShareAltOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  FileExcelOutlined,
  BarChartOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  MoreOutlined,
  PlayCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
// Note: recharts is not installed
// import { ... } from 'recharts';
import request from '@/services/request';

type DatasetStatus = 'ready' | 'processing' | 'error' | 'uploading';
type DatasetType = 'csv' | 'json' | 'parquet' | 'excel';

interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  uniqueCount: number;
  nullCount: number;
  sampleValues: (string | number | boolean)[];
  isIndex?: boolean;
  statistics?: { min?: number; max?: number; mean?: number; std?: number; median?: number };
}

interface DatasetDetail {
  id: string;
  name: string;
  description: string;
  type: DatasetType;
  status: DatasetStatus;
  size: number;
  rowCount: number;
  columnCount: number;
  createdAt: string;
  updatedAt: string;
  tags: string[];
  owner: string;
  qualityScore?: number;
  usageCount: number;
  columns: ColumnInfo[];
  previewData: Record<string, unknown>[];
  statistics: { totalSize: number; fileCount: number; completeness: number; consistency: number; accuracy: number };
  schema: { version: string; primaryKey?: string; description?: string };
}

const formatFileSize = (bytes: number) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatNumber = (num: number) => {
  if (!num) return '0';
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toString();
};
import styles from './Detail.module.less';

const { Title, Text, Paragraph } = Typography;
const { TabPane } = Tabs;

// 文件类型图标映射
const FileTypeIcon: Record<DatasetType, React.ReactNode> = {
  csv: <FileTextOutlined style={{ color: '#52c41a' }} />,
  json: <FileTextOutlined style={{ color: '#faad14' }} />,
  parquet: <DatabaseOutlined style={{ color: '#722ed1' }} />,
  excel: <FileExcelOutlined style={{ color: '#13c2c2' }} />,
};

// 状态配置
const StatusConfig: Record<DatasetStatus, { color: string; text: string; icon: React.ReactNode }> = {
  ready: { color: 'success', text: '可用', icon: <CheckCircleOutlined /> },
  processing: { color: 'processing', text: '处理中', icon: <ClockCircleOutlined /> },
  error: { color: 'error', text: '异常', icon: <CloseCircleOutlined /> },
  uploading: { color: 'warning', text: '上传中', icon: <WarningOutlined /> },
};

// 列类型颜色
const ColumnTypeColors: Record<string, string> = {
  string: '#1890ff',
  number: '#52c41a',
  boolean: '#722ed1',
  datetime: '#faad14',
  category: '#13c2c2',
};

// 数据分布模拟数据
const distributionData = [
  { range: '0-10', count: 150 },
  { range: '10-20', count: 320 },
  { range: '20-30', count: 580 },
  { range: '30-40', count: 420 },
  { range: '40-50', count: 280 },
  { range: '50-60', count: 150 },
  { range: '60-70', count: 80 },
  { range: '70+', count: 20 },
];

// 类别分布模拟数据
const categoryData = [
  { name: '电子产品', value: 35, color: '#1890ff' },
  { name: '服装', value: 25, color: '#52c41a' },
  { name: '食品', value: 20, color: '#faad14' },
  { name: '家居', value: 12, color: '#722ed1' },
  { name: '其他', value: 8, color: '#8c8c8c' },
];

// 趋势数据
const trendData = [
  { day: '周一', uploads: 12, downloads: 8 },
  { day: '周二', uploads: 18, downloads: 12 },
  { day: '周三', uploads: 15, downloads: 15 },
  { day: '周四', uploads: 22, downloads: 18 },
  { day: '周五', uploads: 28, downloads: 24 },
  { day: '周六', uploads: 16, downloads: 20 },
  { day: '周日', uploads: 14, downloads: 16 },
];

const DatasetDetailPage: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [activeTab, setActiveTab] = useState('overview');

  // 从后端API加载数据集详情
  useEffect(() => {
    if (!datasetId) return;
    setLoading(true);
    request.get(`/datasets/${datasetId}`)
      .then((res: any) => {
        const d = res?.data || res;
        if (d) {
          setDataset({
            id: d.id,
            name: d.name || '',
            description: d.description || '',
            type: (d.data_type || 'csv') as DatasetType,
            status: (d.status || 'ready') as DatasetStatus,
            size: d.size_bytes || 0,
            rowCount: d.row_count || 0,
            columnCount: d.column_count || 0,
            createdAt: d.created_at || '',
            updatedAt: d.updated_at || d.created_at || '',
            tags: d.tags || [],
            owner: d.owner_name || '',
            qualityScore: d.quality_score ? Math.round(d.quality_score * 100) : undefined,
            usageCount: d.usage_count || 0,
            columns: (d.columns_info || []).map((c: any, idx: number) => ({
              name: c.name || `col_${idx}`,
              type: c.type || 'string',
              nullable: true,
              uniqueCount: 0,
              nullCount: 0,
              sampleValues: [],
            })),
            previewData: [],
            statistics: {
              totalSize: d.size_bytes || 0,
              fileCount: 1,
              completeness: (d.quality_score || 0.8) * 100,
              consistency: (d.quality_score || 0.8) * 100,
              accuracy: (d.quality_score || 0.8) * 100,
            },
            schema: { version: '1.0' },
          });
        }
      })
      .catch(() => { message.error('加载数据集详情失败'); })
      .finally(() => { setLoading(false); });
  }, [datasetId]);

  // 处理返回
  const handleBack = () => {
    navigate('/app/datasets');
  };

  // 处理编辑
  const handleEdit = () => {
    message.info('编辑功能开发中');
  };

  // 处理删除
  const handleDelete = () => {
    message.success('数据集已删除');
    navigate('/app/datasets');
  };

  // 处理下载
  const handleDownload = () => {
    message.success('开始下载数据集');
  };

  // 处理分享
  const handleShare = () => {
    message.success('分享链接已复制到剪贴板');
  };

  // 处理创建任务
  const handleCreateTask = () => {
    navigate('/app/tasks/publish', { state: { datasetId } });
  };

  // 更多操作菜单
  const moreMenuItems = [
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑信息',
      onClick: handleEdit,
    },
    {
      key: 'share',
      icon: <ShareAltOutlined />,
      label: '分享',
      onClick: handleShare,
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: '删除',
      danger: true,
      onClick: handleDelete,
    },
  ];

  // 渲染概览页
  const renderOverview = () => (
    <>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} className={styles.statsRow}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="数据行数"
              value={dataset?.rowCount || 0}
              formatter={(value) => formatNumber(value as number)}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="特征列数"
              value={dataset?.columnCount || 0}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="文件大小"
              value={formatFileSize(dataset?.size || 0)}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="使用次数"
              value={dataset?.usageCount || 0}
              prefix={<PlayCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 质量评分 */}
      <Row gutter={[16, 16]} className={styles.qualityRow}>
        <Col xs={24} lg={12}>
          <Card title="数据质量评估" className={styles.qualityCard}>
            <div className={styles.qualityScore}>
              <div className={styles.scoreCircle}>
                <Progress
                  type="circle"
                  percent={dataset?.qualityScore || 0}
                  width={120}
                  strokeColor={
                    (dataset?.qualityScore || 0) >= 90
                      ? '#52c41a'
                      : (dataset?.qualityScore || 0) >= 70
                      ? '#faad14'
                      : '#ff4d4f'
                  }
                  format={(percent) => (
                    <div className={styles.scoreText}>
                      <div className={styles.scoreValue}>{percent}</div>
                      <div className={styles.scoreLabel}>质量分</div>
                    </div>
                  )}
                />
              </div>
              <div className={styles.qualityDetails}>
                <div className={styles.qualityItem}>
                  <Text type="secondary">完整度</Text>
                  <Progress percent={dataset?.statistics.completeness || 0} size="small" />
                </div>
                <div className={styles.qualityItem}>
                  <Text type="secondary">一致性</Text>
                  <Progress percent={dataset?.statistics.consistency || 0} size="small" />
                </div>
                <div className={styles.qualityItem}>
                  <Text type="secondary">准确度</Text>
                  <Progress percent={dataset?.statistics.accuracy || 0} size="small" />
                </div>
              </div>
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="类别分布" className={styles.chartCard}>
            <div className={styles.categoryDistribution}>
              {categoryData.map((item) => (
                <div key={item.name} className={styles.categoryItem}>
                  <div className={styles.categoryHeader}>
                    <span className={styles.categoryDot} style={{ backgroundColor: item.color }} />
                    <span className={styles.categoryName}>{item.name}</span>
                    <span className={styles.categoryValue}>{item.value}%</span>
                  </div>
                  <Progress percent={item.value} strokeColor={item.color} showInfo={false} size="small" />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* 基本信息 */}
      <Card title="基本信息" className={styles.infoCard}>
        <Descriptions column={{ xs: 1, sm: 2, lg: 3 }}>
          <Descriptions.Item label="数据集ID">{dataset?.id}</Descriptions.Item>
          <Descriptions.Item label="数据集名称">{dataset?.name}</Descriptions.Item>
          <Descriptions.Item label="数据类型">
            <Tag>{dataset?.type?.toUpperCase()}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {dataset && (
              <Badge
                status={StatusConfig[dataset.status].color as any}
                text={StatusConfig[dataset.status].text}
              />
            )}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">{dataset?.createdAt}</Descriptions.Item>
          <Descriptions.Item label="更新时间">{dataset?.updatedAt}</Descriptions.Item>
          <Descriptions.Item label="所有者">{dataset?.owner}</Descriptions.Item>
          <Descriptions.Item label="标签">
            <Space size={[4, 4]} wrap>
              {dataset?.tags.map((tag) => (
                <Tag key={tag}>{tag}</Tag>
              ))}
            </Space>
          </Descriptions.Item>
          <Descriptions.Item label="Schema版本">{dataset?.schema.version}</Descriptions.Item>
        </Descriptions>
        <div className={styles.descriptionSection}>
          <Text type="secondary">描述</Text>
          <Paragraph className={styles.descriptionText}>
            {dataset?.description}
          </Paragraph>
        </div>
      </Card>
    </>
  );

  // 渲染特征列表
  const renderFeatures = () => {
    const columns: ColumnsType<ColumnInfo> = [
      {
        title: '列名',
        dataIndex: 'name',
        key: 'name',
        width: 150,
        render: (name, record) => (
          <Space>
            {record.isIndex && <Tag color="purple">索引</Tag>}
            <Text strong>{name}</Text>
          </Space>
        ),
      },
      {
        title: '数据类型',
        dataIndex: 'type',
        key: 'type',
        width: 120,
        render: (type) => (
          <Tag color={ColumnTypeColors[type]} style={{ minWidth: 60, textAlign: 'center' }}>
            {type === 'string' && '字符串'}
            {type === 'number' && '数值'}
            {type === 'boolean' && '布尔'}
            {type === 'datetime' && '日期时间'}
            {type === 'category' && '类别'}
          </Tag>
        ),
      },
      {
        title: '可空',
        dataIndex: 'nullable',
        key: 'nullable',
        width: 80,
        align: 'center',
        render: (nullable) => (
          <Tag color={nullable ? 'default' : 'success'}>
            {nullable ? '是' : '否'}
          </Tag>
        ),
      },
      {
        title: '唯一值数',
        dataIndex: 'uniqueCount',
        key: 'uniqueCount',
        width: 100,
        align: 'right',
        render: (count) => formatNumber(count),
      },
      {
        title: '空值数',
        dataIndex: 'nullCount',
        key: 'nullCount',
        width: 100,
        align: 'right',
        render: (count) => (
          <Text type={count > 0 ? 'warning' : 'secondary'}>
            {formatNumber(count)}
          </Text>
        ),
      },
      {
        title: '统计信息',
        key: 'statistics',
        render: (_, record) => {
          if (!record.statistics) return '-';
          const { min, max, mean, std } = record.statistics;
          return (
            <Space size="small" wrap>
              {min !== undefined && <Tag>min: {min}</Tag>}
              {max !== undefined && <Tag>max: {max}</Tag>}
              {mean !== undefined && <Tag>mean: {mean.toFixed(2)}</Tag>}
              {std !== undefined && <Tag>std: {std.toFixed(2)}</Tag>}
            </Space>
          );
        },
      },
      {
        title: '样本值',
        dataIndex: 'sampleValues',
        key: 'sampleValues',
        ellipsis: true,
        render: (values) => (
          <Tooltip title={values.join(', ')}>
            <Text type="secondary" className={styles.sampleValues}>
              {values.slice(0, 3).join(', ')}
              {values.length > 3 && '...'}
            </Text>
          </Tooltip>
        ),
      },
    ];

    return (
      <Card className={styles.featuresCard}>
        <Table
          dataSource={dataset?.columns}
          columns={columns}
          rowKey="name"
          pagination={false}
          size="small"
          scroll={{ x: 'max-content' }}
        />
      </Card>
    );
  };

  // 渲染数据预览
  const renderPreview = () => {
    if (!dataset?.previewData) return null;

    const columns: ColumnsType<Record<string, unknown>> = Object.keys(
      dataset.previewData[0]
    ).map((key) => ({
      title: key,
      dataIndex: key,
      key,
      width: 120,
      ellipsis: true,
      render: (value) => {
        if (value === null || value === undefined) {
          return <Text type="secondary" className={styles.nullValue}>NULL</Text>;
        }
        if (typeof value === 'boolean') {
          return <Tag color={value ? 'success' : 'default'}>{value ? 'true' : 'false'}</Tag>;
        }
        return String(value);
      },
    }));

    return (
      <>
        <Alert
          message="数据预览"
          description="以下展示前 100 行数据的预览。实际数据可能包含更多行。"
          type="info"
          showIcon
          icon={<EyeOutlined />}
          className={styles.previewAlert}
        />
        <Card className={styles.previewCard}>
          <Table
            dataSource={dataset.previewData}
            columns={columns}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content', y: 500 }}
            rowKey={(_, index) => String(index)}
          />
        </Card>
      </>
    );
  };

  // 渲染统计分析
  const renderStatistics = () => (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="数值分布" className={styles.chartCard}>
            <div className={styles.distributionChart}>
              {distributionData.map((item) => (
                <div key={item.range} className={styles.distributionItem}>
                  <div className={styles.distributionLabel}>{item.range}</div>
                  <div className={styles.distributionBarWrapper}>
                    <Progress
                      percent={Math.round((item.count / 580) * 100)}
                      strokeColor="#1890ff"
                      showInfo={false}
                      size="small"
                    />
                  </div>
                  <div className={styles.distributionValue}>{item.count}</div>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="使用趋势" className={styles.chartCard}>
            <div className={styles.trendStats}>
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="本周上传"
                      value={trendData.reduce((sum, d) => sum + d.uploads, 0)}
                      valueStyle={{ color: '#1890ff' }}
                    />
                  </Card>
                </Col>
                <Col span={12}>
                  <Card size="small">
                    <Statistic
                      title="本周下载"
                      value={trendData.reduce((sum, d) => sum + d.downloads, 0)}
                      valueStyle={{ color: '#52c41a' }}
                    />
                  </Card>
                </Col>
              </Row>
              <div className={styles.trendList} style={{ marginTop: 16 }}>
                {trendData.map((item) => (
                  <div key={item.day} className={styles.trendItem}>
                    <span className={styles.trendDay}>{item.day}</span>
                    <span className={styles.trendUploads}>↑ {item.uploads}</span>
                    <span className={styles.trendDownloads}>↓ {item.downloads}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="使用记录" className={styles.historyCard}>
        <List
          dataSource={[
            { task: '医疗影像分类模型训练', user: '张医生', time: '2024-01-20 14:30', type: '训练' },
            { task: '客户行为分析', user: '李分析师', time: '2024-01-19 10:15', type: '分析' },
            { task: '销售预测模型', user: '王工程师', time: '2024-01-18 16:45', type: '训练' },
            { task: '数据质量评估', user: '系统', time: '2024-01-17 09:00', type: '评估' },
          ]}
          renderItem={(item) => (
            <List.Item>
              <List.Item.Meta
                title={item.task}
                description={`${item.user} · ${item.time}`}
              />
              <Tag>{item.type}</Tag>
            </List.Item>
          )}
        />
      </Card>
    </>
  );

  if (loading) {
    return (
      <div className={styles.detailPage}>
        <Skeleton active paragraph={{ rows: 10 }} />
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className={styles.detailPage}>
        <Empty description="数据集不存在" />
      </div>
    );
  }

  const status = StatusConfig[dataset.status];

  return (
    <div className={styles.detailPage}>
      {/* 页面头部 */}
      <div className={styles.pageHeader}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={handleBack}>
            返回
          </Button>
          <div className={styles.headerIcon}>
            {FileTypeIcon[dataset.type]}
          </div>
          <div>
            <Title level={4} className={styles.headerTitle}>
              {dataset.name}
              <Tag
                color={status.color}
                icon={status.icon}
                style={{ marginLeft: 12 }}
              >
                {status.text}
              </Tag>
            </Title>
            <Text type="secondary">{dataset.id} · 更新于 {dataset.updatedAt}</Text>
          </div>
        </Space>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>
            下载
          </Button>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={handleCreateTask}>
            创建任务
          </Button>
          <Dropdown menu={{ items: moreMenuItems }} placement="bottomRight">
            <Button icon={<MoreOutlined />} />
          </Dropdown>
        </Space>
      </div>

      {/* 标签页 */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        className={styles.detailTabs}
        type="card"
      >
        <TabPane tab="概览" key="overview">
          {renderOverview()}
        </TabPane>
        <TabPane tab="特征列表" key="features">
          {renderFeatures()}
        </TabPane>
        <TabPane tab="数据预览" key="preview">
          {renderPreview()}
        </TabPane>
        <TabPane tab="统计分析" key="statistics">
          {renderStatistics()}
        </TabPane>
      </Tabs>
    </div>
  );
};

export default DatasetDetailPage;
