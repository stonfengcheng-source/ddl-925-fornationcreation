import React from 'react';
import { Card as AntCard, Badge, Progress, Space, Tag, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  CloudOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { TrainingNode, NodeStatus } from '../../../../types/training';

interface NodeStatusCardProps {
  node: TrainingNode;
}

const NodeStatusCard: React.FC<NodeStatusCardProps> = ({ node }) => {
  // 状态配置
  const statusConfig: Record<NodeStatus, { color: string; icon: React.ReactNode; text: string; bgColor: string }> = {
    online: {
      color: '#52c41a',
      icon: <CheckCircleOutlined />,
      text: '在线',
      bgColor: '#f6ffed',
    },
    offline: {
      color: '#d9d9d9',
      icon: <CloudOutlined />,
      text: '离线',
      bgColor: '#fafafa',
    },
    training: {
      color: '#1890ff',
      icon: <SyncOutlined spin />,
      text: '训练中',
      bgColor: '#e6f7ff',
    },
    error: {
      color: '#ff4d4f',
      icon: <ExclamationCircleOutlined />,
      text: '错误',
      bgColor: '#fff2f0',
    },
    syncing: {
      color: '#faad14',
      icon: <ClockCircleOutlined />,
      text: '同步中',
      bgColor: '#fffbe6',
    },
  };

  const config = statusConfig[node.status];

  // 心跳时间格式化
  const formatLastHeartbeat = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return `${seconds}秒前`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}分钟前`;
    const hours = Math.floor(minutes / 60);
    return `${hours}小时前`;
  };

  return (
    <AntCard
      size="small"
      className="h-full"
      style={{ background: config.bgColor, borderColor: config.color }}
      title={
        <Space>
          <span style={{ color: config.color }}>{config.icon}</span>
          <span className="font-medium">{node.name}</span>
          {node.role === 'aggregator' && <Tag color="blue">聚合</Tag>}
        </Space>
      }
      extra={
        <Badge
          color={config.color}
          text={<span style={{ color: config.color }}>{config.text}</span>}
        />
      }
    >
      <div className="space-y-3">
        {/* 节点ID */}
        <div className="text-xs text-gray-500 truncate">{node.nodeId}</div>

        {/* 训练进度 */}
        {node.status === 'training' && node.trainingProgress !== undefined && (
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>训练进度</span>
              <span>{node.currentRound}轮</span>
            </div>
            <Progress
              percent={node.trainingProgress}
              size="small"
              strokeColor={config.color}
              showInfo={false}
            />
          </div>
        )}

        {/* 统计信息 */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <Tooltip title="数据样本数">
            <div className="flex items-center gap-1 text-gray-600">
              <DatabaseOutlined />
              <span>{node.dataSampleCount.toLocaleString()}</span>
            </div>
          </Tooltip>
          <Tooltip title="网络延迟">
            <div className="flex items-center gap-1 text-gray-600">
              <ThunderboltOutlined />
              <span>{node.latency}ms</span>
            </div>
          </Tooltip>
          <Tooltip title="已获得奖励">
            <div className="flex items-center gap-1 text-gray-600">
              <DollarOutlined />
              <span>¥{node.earnedReward.toLocaleString()}</span>
            </div>
          </Tooltip>
          <Tooltip title="贡献度分数">
            <div className="flex items-center gap-1 text-gray-600">
              <span className="text-xs">贡献</span>
              <span>{node.contributionScore.toFixed(1)}</span>
            </div>
          </Tooltip>
        </div>

        {/* 心跳时间 */}
        <div className="text-xs text-gray-400 text-right">
          心跳: {formatLastHeartbeat(node.lastHeartbeat)}
        </div>
      </div>
    </AntCard>
  );
};

export default NodeStatusCard;
