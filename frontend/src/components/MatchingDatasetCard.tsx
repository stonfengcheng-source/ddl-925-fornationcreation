/**
 * 匹配数据集卡片组件
 * 展示数据集信息和语义匹配分数（Buyer视角）
 */
import React from 'react';
import { Card, Button, Tag, Space, Typography, Tooltip } from 'antd';
import { DatabaseOutlined, UserOutlined, BarChartOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { MatchingDataset } from '@/types/training';
import SimilarityScore from './SimilarityScore';

const { Text, Title } = Typography;

interface MatchingDatasetCardProps {
  dataset: MatchingDataset;
  onViewDetail?: (datasetId: string) => void;
  onInvite?: (datasetId: string) => void;
  loading?: boolean;
  alreadyInvited?: boolean;
}

export const MatchingDatasetCard: React.FC<MatchingDatasetCardProps> = ({
  dataset,
  onViewDetail,
  onInvite,
  loading = false,
  alreadyInvited = false,
}) => {
  const {
    dataset_id,
    dataset_name,
    description,
    data_type,
    row_count,
    owner_id,
    scores,
  } = dataset;

  // 格式化数据量显示
  const formatDataSize = (count?: number): string => {
    if (!count) return '-';
    if (count >= 10000) {
      return `${(count / 10000).toFixed(1)}万条`;
    }
    return `${count.toLocaleString()}条`;
  };

  return (
    <Card
      className="hover:shadow-lg transition-shadow duration-300"
      bodyStyle={{ padding: '16px' }}
      actions={[
        <Button
          key="detail"
          type="link"
          onClick={() => onViewDetail?.(dataset_id)}
        >
          查看详情
        </Button>,
        alreadyInvited ? (
          <Button
            key="invited"
            type="link"
            disabled
            icon={<CheckCircleOutlined />}
          >
            已邀请
          </Button>
        ) : (
          <Button
            key="invite"
            type="primary"
            loading={loading}
            onClick={() => onInvite?.(dataset_id)}
          >
            邀请参与
          </Button>
        ),
      ]}
    >
      {/* 头部：标题和数据类型 */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1 mr-2">
          <Title level={5} className="!mb-1 !text-base line-clamp-1">
            {dataset_name}
          </Title>
          {data_type && (
            <Tag color="green">
              {data_type}
            </Tag>
          )}
        </div>
        <Tooltip title="数据拥有者">
          <Tag icon={<UserOutlined />} color="default">
            {owner_id ? owner_id.substring(0, 8) : '未知'}
          </Tag>
        </Tooltip>
      </div>

      {/* 描述 */}
      {description && (
        <Text className="text-gray-500 text-sm line-clamp-2 block mb-3">
          {description}
        </Text>
      )}

      {/* 相似度分数 */}
      <div className="mb-3 p-3 bg-gray-50 rounded-lg">
        <SimilarityScore scores={scores} size="small" showDetails />
      </div>

      {/* 底部信息 */}
      <Space className="text-sm text-gray-600">
        <span>
          <DatabaseOutlined className="mr-1" />
          数据量: {formatDataSize(row_count)}
        </span>
        <span>
          <BarChartOutlined className="mr-1" />
          匹配度: {Math.round(scores.total * 100)}%
        </span>
      </Space>
    </Card>
  );
};

export default MatchingDatasetCard;
