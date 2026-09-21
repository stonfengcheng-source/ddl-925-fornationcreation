/**
 * 数据集列表页面
 * 路径: /datasets
 * 功能: 展示所有数据集的卡片网格，支持搜索筛选
 */

import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Row,
  Col,
  Card,
  Input,
  Select,
  Tag,
  Button,
  Empty,
  Space,
  Typography,
  Badge,
  Tooltip,
  Dropdown,
  Spin,
  message,
} from 'antd';
import {
  SearchOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  FileExcelOutlined,
  MoreOutlined,
  EyeOutlined,
  DeleteOutlined,
  EditOutlined,
  CloudUploadOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import request from '@/services/request';

// 类型定义（原来从mock导入，现在本地定义）
export type DatasetStatus = 'ready' | 'processing' | 'error' | 'uploading';
export type DatasetType = 'csv' | 'json' | 'parquet' | 'excel';

export interface Dataset {
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
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatNumber = (num: number) => {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M';
  if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K';
  return num.toString();
};
import styles from './index.module.less';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// 文件类型图标映射
const FileTypeIcon: Record<DatasetType, React.ReactNode> = {
  csv: <FileTextOutlined style={{ color: '#52c41a' }} />,
  json: <FileTextOutlined style={{ color: '#faad14' }} />,
  parquet: <DatabaseOutlined style={{ color: '#722ed1' }} />,
  excel: <FileExcelOutlined style={{ color: '#13c2c2' }} />,
};

// 状态标签配置
const StatusConfig: Record<DatasetStatus, { color: string; text: string }> = {
  ready: { color: 'success', text: '可用' },
  processing: { color: 'processing', text: '处理中' },
  error: { color: 'error', text: '异常' },
  uploading: { color: 'warning', text: '上传中' },
};

// 数据集卡片组件
interface DatasetCardProps {
  dataset: Dataset;
  onView: (id: string) => void;
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, onView, onEdit, onDelete }) => {
  const status = StatusConfig[dataset.status];

  const menuItems = [
    {
      key: 'view',
      icon: <EyeOutlined />,
      label: '查看详情',
      onClick: () => onView(dataset.id),
    },
    {
      key: 'edit',
      icon: <EditOutlined />,
      label: '编辑',
      onClick: () => onEdit(dataset.id),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'delete',
      icon: <DeleteOutlined />,
      label: '删除',
      danger: true,
      onClick: () => onDelete(dataset.id),
    },
  ];

  return (
    <Card
      className={styles.datasetCard}
      hoverable={dataset.status === 'ready'}
      onClick={() => dataset.status === 'ready' && onView(dataset.id)}
    >
      <div className={styles.cardHeader}>
        <div className={styles.fileIcon}>
          {FileTypeIcon[dataset.type]}
        </div>
        <div className={styles.headerActions}>
          <Badge status={status.color as any} text={status.text} />
          <Dropdown
            menu={{ items: menuItems }}
            placement="bottomRight"
            trigger={['click']}
          >
            <Button
              type="text"
              icon={<MoreOutlined />}
              className={styles.moreBtn}
              onClick={(e) => e.stopPropagation()}
            />
          </Dropdown>
        </div>
      </div>

      <div className={styles.cardContent}>
        <Tooltip title={dataset.name}>
          <Title level={5} className={styles.datasetName} ellipsis>
            {dataset.name}
          </Title>
        </Tooltip>
        <Paragraph
          type="secondary"
          className={styles.datasetDesc}
          ellipsis={{ rows: 2 }}
        >
          {dataset.description}
        </Paragraph>
      </div>

      <div className={styles.cardStats}>
        <div className={styles.statItem}>
          <Text type="secondary">行数</Text>
          <Text strong>{formatNumber(dataset.rowCount)}</Text>
        </div>
        <div className={styles.statItem}>
          <Text type="secondary">列数</Text>
          <Text strong>{dataset.columnCount}</Text>
        </div>
        <div className={styles.statItem}>
          <Text type="secondary">大小</Text>
          <Text strong>{formatFileSize(dataset.size)}</Text>
        </div>
      </div>

      <div className={styles.cardFooter}>
        <Space size={[4, 4]} wrap className={styles.tags}>
          {dataset.tags.slice(0, 3).map((tag) => (
            <Tag key={tag} className={styles.tag}>{tag}</Tag>
          ))}
          {dataset.tags.length > 3 && (
            <Tag className={styles.tag}>+{dataset.tags.length - 3}</Tag>
          )}
        </Space>
        <div className={styles.footerInfo}>
          <Text type="secondary" className={styles.owner}>
            {dataset.owner}
          </Text>
          {dataset.qualityScore && (
            <Tooltip title="数据质量评分">
              <span className={styles.qualityScore}>
                <BarChartOutlined />
                {dataset.qualityScore}
              </span>
            </Tooltip>
          )}
        </div>
      </div>
    </Card>
  );
};

// 主页面组件
const DatasetList: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);

  // 从后端获取数据集
  useEffect(() => {
    const fetchDatasets = async () => {
      setLoading(true);
      try {
        const res: any = await request.get('/datasets');
        const list = res?.data || res || [];
        const mapped: Dataset[] = (Array.isArray(list) ? list : []).map((d: any) => ({
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
        }));
        setDatasets(mapped);
      } catch {
        setDatasets([]);
      } finally {
        setLoading(false);
      }
    };
    fetchDatasets();
  }, []);

  // 从数据中提取所有标签
  const datasetTags = useMemo(() => {
    const tagSet = new Set<string>();
    datasets.forEach((d) => d.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet);
  }, [datasets]);

  // 筛选数据集
  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      // 搜索筛选
      if (searchText) {
        const searchLower = searchText.toLowerCase();
        const matchSearch =
          dataset.name.toLowerCase().includes(searchLower) ||
          dataset.description.toLowerCase().includes(searchLower) ||
          dataset.tags.some((tag) => tag.toLowerCase().includes(searchLower));
        if (!matchSearch) return false;
      }

      // 类型筛选
      if (selectedType !== 'all' && dataset.type !== selectedType) {
        return false;
      }

      // 状态筛选
      if (selectedStatus !== 'all' && dataset.status !== selectedStatus) {
        return false;
      }

      // 标签筛选
      if (selectedTags.length > 0) {
        const hasTag = selectedTags.some((tag) => dataset.tags.includes(tag));
        if (!hasTag) return false;
      }

      return true;
    });
  }, [searchText, selectedType, selectedStatus, selectedTags]);

  // 处理查看
  const handleView = (id: string) => {
    navigate(`/app/datasets/${id}`);
  };

  // 处理编辑
  const handleEdit = (id: string) => {
    message.info(`编辑数据集 ${id}（功能开发中）`);
  };

  // 处理删除
  const handleDelete = async (id: string) => {
    try {
      await request.delete(`/datasets/${id}`);
      message.success('数据集已删除');
      setDatasets((prev) => prev.filter((d) => d.id !== id));
    } catch {
      message.error('删除失败');
    }
  };

  // 处理标签选择
  const handleTagSelect = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
    );
  };

  // 清除筛选
  const clearFilters = () => {
    setSearchText('');
    setSelectedType('all');
    setSelectedStatus('all');
    setSelectedTags([]);
  };

  return (
    <div className={styles.datasetList}>
      {/* 页面标题 */}
      <div className={styles.pageHeader}>
        <div>
          <Title level={3} className={styles.pageTitle}>数据集管理</Title>
          <Text type="secondary">管理和探索您的数据集资源</Text>
        </div>
        <Button
          type="primary"
          icon={<CloudUploadOutlined />}
          size="large"
          onClick={() => navigate('/app/datasets/upload')}
        >
          上传数据集
        </Button>
      </div>

      {/* 筛选栏 */}
      <Card className={styles.filterCard}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={12} lg={8}>
            <Input
              placeholder="搜索数据集名称、描述或标签"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} lg={4}>
            <Select
              placeholder="文件类型"
              value={selectedType}
              onChange={setSelectedType}
              style={{ width: '100%' }}
            >
              <Option value="all">全部类型</Option>
              <Option value="csv">CSV</Option>
              <Option value="json">JSON</Option>
              <Option value="parquet">Parquet</Option>
              <Option value="excel">Excel</Option>
            </Select>
          </Col>
          <Col xs={12} sm={6} lg={4}>
            <Select
              placeholder="状态"
              value={selectedStatus}
              onChange={setSelectedStatus}
              style={{ width: '100%' }}
            >
              <Option value="all">全部状态</Option>
              <Option value="ready">可用</Option>
              <Option value="processing">处理中</Option>
              <Option value="uploading">上传中</Option>
              <Option value="error">异常</Option>
            </Select>
          </Col>
          <Col xs={24} lg={8}>
            <Space wrap>
              {selectedTags.length > 0 && (
                <Button type="link" onClick={clearFilters}>
                  清除筛选
                </Button>
              )}
            </Space>
          </Col>
        </Row>

        {/* 标签筛选 */}
        <div className={styles.tagFilter}>
          <Text type="secondary" className={styles.tagFilterLabel}>标签筛选：</Text>
          <Space size={[8, 8]} wrap>
            {datasetTags.map((tag) => (
              <Tag
                key={tag}
                className={styles.filterTag}
                color={selectedTags.includes(tag) ? 'blue' : undefined}
                onClick={() => handleTagSelect(tag)}
                style={{ cursor: 'pointer' }}
              >
                {tag}
              </Tag>
            ))}
          </Space>
        </div>
      </Card>

      {/* 统计信息 */}
      <div className={styles.statsBar}>
        <Text type="secondary">
          共 <Text strong>{filteredDatasets.length}</Text> 个数据集
          {selectedTags.length > 0 && ` · 已选择 ${selectedTags.length} 个标签`}
        </Text>
      </div>

      {/* 数据集网格 */}
      <Spin spinning={loading}>
      {filteredDatasets.length > 0 ? (
        <Row gutter={[24, 24]}>
          {filteredDatasets.map((dataset) => (
            <Col xs={24} sm={12} lg={8} xl={6} key={dataset.id}>
              <DatasetCard
                dataset={dataset}
                onView={handleView}
                onEdit={handleEdit}
                onDelete={handleDelete}
              />
            </Col>
          ))}
        </Row>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <Space direction="vertical" size="small">
              <Text>没有找到符合条件的数据集</Text>
              <Button type="primary" onClick={clearFilters}>
                清除筛选条件
              </Button>
            </Space>
          }
          className={styles.emptyState}
        />
      )}
      </Spin>
    </div>
  );
};

export default DatasetList;
