/**
 * 推荐任务卡片组件
 * 展示任务基本信息和语义匹配分数
 */
import React from 'react';
import { Card, Button, Tag, Space, Typography } from 'antd';
import { CheckCircleOutlined, TeamOutlined, GiftOutlined } from '@ant-design/icons';
import type { RecommendedTask } from '@/types/training';
import SimilarityScore from './SimilarityScore';

const { Text, Title } = Typography;

interface RecommendedTaskCardProps {
  task: RecommendedTask;
  onViewDetail?: (taskId: string) => void;
  onJoin?: (taskId: string) => void;
  loading?: boolean;
}

export const RecommendedTaskCard: React.FC<RecommendedTaskCardProps> = ({
  task,
  onViewDetail,
  onJoin,
  loading = false,
}) => {
  const {
    task_id,
    task_name,
    description,
    category,
    reward_pool,
    scores,
    status,
    current_participants,
    max_nodes,
    already_joined,
  } = task;

  // 状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '待开始' },
      matching: { color: 'processing', text: '匹配中' },
      running: { color: 'success', text: '进行中' },
      completed: { color: 'success', text: '已完成' },
      failed: { color: 'error', text: '失败' },
    };
    const { color, text } = statusMap[status] || { color: 'default', text: status };
    return <Tag color={color}>{text}</Tag>;
  };

  return (
    <Card
      className="hover:shadow-lg transition-shadow duration-300"
      bodyStyle={{ padding: '16px' }}
      actions={[
        <Button
          key="detail"
          type="link"
          onClick={() => onViewDetail?.(task_id)}
        >
          查看详情
        </Button>,
        already_joined ? (
          <Button
            key="joined"
            type="link"
            disabled
            icon={<CheckCircleOutlined />}
          >
            已参与
          </Button>
        ) : (
          <Button
            key="join"
            type="primary"
            loading={loading}
            onClick={() => onJoin?.(task_id)}
          >
            立即参与
          </Button>
        ),
      ]}
    >
      {/* 头部：标题和类别 */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex-1 mr-2">
          <Title level={5} className="!mb-1 !text-base line-clamp-1">
            {task_name}
          </Title>
          {category && (
            <Tag color="blue">
              {category}
            </Tag>
          )}
        </div>
        {getStatusTag(status)}
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
          <GiftOutlined className="mr-1" />
          奖励: ¥{reward_pool?.toLocaleString()}
        </span>
        <span>
          <TeamOutlined className="mr-1" />
          {current_participants || 0}/{max_nodes || 10} 节点
        </span>
      </Space>
    </Card>
  );
};

export default RecommendedTaskCard;
