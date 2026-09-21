/**
 * 数据资产列表页
 * 展示用户已登记的数据资产画像
 *
 * 功能：
 * - 统计卡片（总数、总规模、平均质量）
 * - 数据资产卡片网格
 * - 快速登记入口
 */

import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import request from '@/services/request';
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
  Statistic,
  Spin,
  message,
} from 'antd';
import {
  SearchOutlined,
  DatabaseOutlined,
  PlusOutlined,
  BarChartOutlined,
  SafetyOutlined,
  CheckCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { Card as UICard } from '@/components/ui/Card';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;

// 数据资产状态
 type AssetStatus = 'available' | 'in-use' | 'offline';

// 数据资产接口
interface DataAsset {
  id: string;
  name: string;
  description?: string;
  localPath: string;
  schema: {
    sampleCount: number;
    featureCount: number;
    dataType: string;
  };
  domainTags: string[];
  qualityScore: number;
  status: AssetStatus;
  matchedTaskCount: number;
  currentTaskId?: string;
  currentTaskName?: string;
  createdAt: string;
}

// 状态配置
const statusConfig: Record<AssetStatus, { label: string; color: string; badge: string }> = {
  available: { label: '可用', color: 'success', badge: 'green' },
  'in-use': { label: '参与中', color: 'processing', badge: 'blue' },
  offline: { label: '离线', color: 'default', badge: 'gray' },
};

// 科研领域标签映射
const domainTagMap: Record<string, { label: string; color: string }> = {
  'medical-imaging': { label: '医学影像', color: 'blue' },
  'genomics': { label: '基因组学', color: 'purple' },
  'clinical-research': { label: '临床研究', color: 'green' },
  'pathology': { label: '病理分析', color: 'magenta' },
  'drug-discovery': { label: '药物研发', color: 'orange' },
  'epidemiology': { label: '流行病学', color: 'cyan' },
  'radiomics': { label: '影像组学', color: 'gold' },
  'multiomics': { label: '多组学', color: 'lime' },
  // 数据类型标签
  'ct-scan': { label: 'CT', color: 'blue' },
  'mri': { label: 'MRI', color: 'purple' },
  'x-ray': { label: 'X光', color: 'geekblue' },
  'ultrasound': { label: '超声', color: 'cyan' },
  'pathology-slide': { label: '病理切片', color: 'magenta' },
  'genomic-sequence': { label: '基因序列', color: 'purple' },
  'gene-expression': { label: '基因表达', color: 'volcano' },
  'mutation-data': { label: '突变数据', color: 'red' },
  'clinical-record': { label: '病历', color: 'green' },
  'lab-result': { label: '检验', color: 'cyan' },
  'vital-signs': { label: '体征', color: 'orange' },
  'radiology-report': { label: '影像报告', color: 'blue' },
  'pathology-report': { label: '病理报告', color: 'magenta' },
  'demographics': { label: '人口学', color: 'default' },
  'follow-up': { label: '随访', color: 'success' },
};

const DataProfileList: React.FC = () => {
  const navigate = useNavigate();
  const [searchText, setSearchText] = useState('');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [assets, setAssets] = useState<DataAsset[]>([]);
  const [loading, setLoading] = useState(true);

  // 从后端获取数据资产（我的数据）
  useEffect(() => {
    const fetchAssets = async () => {
      setLoading(true);
      try {
        const res: any = await request.get('/datasets/my');
        const list = res?.data || res || [];
        const mapped: DataAsset[] = (Array.isArray(list) ? list : []).map((d: any) => ({
          id: d.id,
          name: d.name,
          description: d.description || '',
          localPath: '',
          schema: {
            sampleCount: d.row_count || 0,
            featureCount: d.column_count || 0,
            dataType: d.data_type || 'csv',
          },
          domainTags: d.tags || [],
          qualityScore: d.quality_score || 0,
          status: (d.status === 'ready' ? 'available' : d.status === 'in-use' ? 'in-use' : 'available') as AssetStatus,
          matchedTaskCount: d.usage_count || 0,
          createdAt: d.created_at || '',
        }));
        setAssets(mapped);
      } catch {
        setAssets([]);
      } finally {
        setLoading(false);
      }
    };
    fetchAssets();
  }, []);

  // 过滤数据
  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const matchSearch = asset.name.toLowerCase().includes(searchText.toLowerCase()) ||
        asset.description?.toLowerCase().includes(searchText.toLowerCase());
      const matchStatus = filterStatus === 'all' || asset.status === filterStatus;
      return matchSearch && matchStatus;
    });
  }, [searchText, filterStatus, assets]);

  // 统计数据
  const stats = useMemo(() => {
    const total = assets.length;
    const totalSamples = assets.reduce((sum, a) => sum + a.schema.sampleCount, 0);
    const avgQuality = assets.reduce((sum, a) => sum + a.qualityScore, 0) / total || 0;
    const inUseCount = assets.filter((a) => a.status === 'in-use').length;
    return { total, totalSamples, avgQuality, inUseCount };
  }, [assets]);

  // 前往登记
  const goToCreate = () => {
    navigate('/app/data-assets/create');
  };

  // 查看详情
  const viewDetail = (_id: string) => {
    message.info('详情功能开发中...');
  };

  // 查看匹配任务
  const viewMatchedTasks = (_id: string) => {
    navigate('/app/matching');
  };

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <Title level={3}>我的数据资产</Title>
          <Paragraph type="secondary">
            管理您的本地数据资产，查看匹配的任务机会
          </Paragraph>
        </div>
        <Button type="primary" onClick={goToCreate} icon={<PlusOutlined />}>
          登记新数据
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card>
            <Statistic
              title="已登记数据"
              value={stats.total}
              suffix="个"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="总样本量"
              value={stats.totalSamples.toLocaleString()}
              suffix="例"
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均质量分"
              value={Math.round(stats.avgQuality * 100)}
              suffix="分"
              prefix={<SafetyOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="参与中任务"
              value={stats.inUseCount}
              suffix="个"
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <div className="flex gap-4">
        <Input
          placeholder="搜索数据资产名称"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 300 }}
        />
        <Select
          placeholder="状态筛选"
          value={filterStatus}
          onChange={setFilterStatus}
          style={{ width: 150 }}
        >
          <Option value="all">全部状态</Option>
          <Option value="available">可用</Option>
          <Option value="in-use">参与中</Option>
          <Option value="offline">离线</Option>
        </Select>
      </div>

      {/* 数据资产卡片网格 */}
      <Spin spinning={loading}>
      {filteredAssets.length > 0 ? (
        <Row gutter={[16, 16]}>
          {filteredAssets.map((asset) => {
            const status = statusConfig[asset.status];
            return (
              <Col span={8} key={asset.id}>
                <UICard variant="default" hoverEffect className="h-full">
                  <div className="flex justify-between items-start mb-4">
                    <div className="flex-1">
                      <Title level={5} className="mb-1">
                        <DatabaseOutlined className="mr-2 text-blue-500" />
                        {asset.name}
                      </Title>
                      <Text type="secondary" className="text-sm">
                        {asset.description}
                      </Text>
                    </div>
                    <Badge status={status.badge as any} text={status.label} />
                  </div>

                  {/* 统计信息 */}
                  <div className="grid grid-cols-3 gap-4 mb-4">
                    <div>
                      <Text type="secondary" className="text-xs">样本量</Text>
                      <div className="font-medium">{asset.schema.sampleCount.toLocaleString()}</div>
                    </div>
                    <div>
                      <Text type="secondary" className="text-xs">特征数</Text>
                      <div className="font-medium">{asset.schema.featureCount}</div>
                    </div>
                    <div>
                      <Text type="secondary" className="text-xs">质量分</Text>
                      <div className="font-medium text-green-600">
                        {Math.round(asset.qualityScore * 100)}
                      </div>
                    </div>
                  </div>

                  {/* 领域标签 */}
                  <div className="mb-4">
                    <Space size={[4, 4]} wrap>
                      {asset.domainTags.map((tag) => {
                        const config = domainTagMap[tag];
                        return (
                          <Tag key={tag} color={config?.color || 'default'}>
                            {config?.label || tag}
                          </Tag>
                        );
                      })}
                    </Space>
                  </div>

                  {/* 匹配任务 */}
                  {asset.matchedTaskCount > 0 && (
                    <div className="bg-gray-50 rounded p-3 mb-4">
                      <div className="flex justify-between items-center">
                        <Text type="secondary" className="text-sm">
                          匹配到 {asset.matchedTaskCount} 个任务
                        </Text>
                        <Button type="link" size="small" onClick={() => viewMatchedTasks(asset.id)}>
                          查看
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* 当前参与任务 */}
                  {asset.status === 'in-use' && asset.currentTaskName && (
                    <div className="bg-blue-50 rounded p-3 mb-4">
                      <Text type="secondary" className="text-sm">
                        当前参与：
                      </Text>
                      <Text className="text-sm ml-1">{asset.currentTaskName}</Text>
                    </div>
                  )}

                  {/* 操作按钮 */}
                  <div className="flex gap-2">
                    <Button
                      icon={<EyeOutlined />}
                      onClick={() => viewDetail(asset.id)}
                      block
                    >
                      查看详情
                    </Button>
                  </div>
                </UICard>
              </Col>
            );
          })}
        </Row>
      ) : (
        <Empty
          description="暂无数据资产"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        >
          <Button type="primary" icon={<PlusOutlined />} onClick={goToCreate}>
            登记第一个数据
          </Button>
        </Empty>
      )}
      </Spin>
    </div>
  );
};

export default DataProfileList;
