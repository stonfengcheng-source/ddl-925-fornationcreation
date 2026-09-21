import React from 'react';
import { Card, Progress, Tooltip, Badge } from 'antd';
import { SafetyOutlined, WarningOutlined, CheckCircleOutlined } from '@ant-design/icons';
import type { PrivacyBudgetCardProps } from '@/types/training';

/**
 * PrivacyBudgetCard 组件
 * 展示单个节点或任务的隐私预算信息
 * 使用橙色主题（与Matching页面一致）
 */
const PrivacyBudgetCard: React.FC<PrivacyBudgetCardProps> = ({
  epsilon,
  epsilonConsumed,
  delta,
  threshold = 80,
  showProgress = true,
  size = 'medium',
  nodeName,
}) => {
  // 计算消耗比例
  const consumptionRate = Math.min(100, (epsilonConsumed / epsilon) * 100);
  const remainingRate = 100 - consumptionRate;

  // 确定状态
  const getStatus = (): 'safe' | 'warning' | 'exhausted' => {
    if (consumptionRate >= 100) return 'exhausted';
    if (consumptionRate >= threshold) return 'warning';
    return 'safe';
  };

  const status = getStatus();

  // 状态配置
  const statusConfig = {
    safe: {
      color: '#52c41a',
      bgColor: '#f6ffed',
      borderColor: '#b7eb8f',
      icon: <CheckCircleOutlined />,
      text: '预算充足',
    },
    warning: {
      color: '#fa8c16',
      bgColor: '#fff7e6',
      borderColor: '#ffd591',
      icon: <WarningOutlined />,
      text: '即将耗尽',
    },
    exhausted: {
      color: '#f5222d',
      bgColor: '#fff1f0',
      borderColor: '#ffa39e',
      icon: <WarningOutlined />,
      text: '预算已耗尽',
    },
  };

  const config = statusConfig[status];

  // 尺寸配置
  const sizeConfig = {
    small: {
      cardPadding: '12px',
      titleSize: '14px',
      valueSize: '20px',
      progressHeight: 6,
    },
    medium: {
      cardPadding: '16px',
      titleSize: '16px',
      valueSize: '28px',
      progressHeight: 8,
    },
    large: {
      cardPadding: '20px',
      titleSize: '18px',
      valueSize: '36px',
      progressHeight: 10,
    },
  };

  const s = sizeConfig[size];

  return (
    <Card
      size="small"
      style={{
        background: config.bgColor,
        borderColor: config.borderColor,
        padding: s.cardPadding,
      }}
      bodyStyle={{ padding: 0 }}
    >
      <div style={{ marginBottom: size === 'small' ? 8 : 12 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 8,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SafetyOutlined style={{ color: config.color, fontSize: s.titleSize }} />
            <span
              style={{
                fontSize: s.titleSize,
                fontWeight: 500,
                color: '#262626',
              }}
            >
              {nodeName || '隐私预算'}
            </span>
          </div>
          <Tooltip title={config.text}>
            <Badge
              count={config.icon}
              style={{
                backgroundColor: config.color,
                color: '#fff',
              }}
            />
          </Tooltip>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
          <span
            style={{
              fontSize: s.valueSize,
              fontWeight: 600,
              color: config.color,
            }}
          >
            ε = {epsilonConsumed.toFixed(3)}
          </span>
          <span
            style={{
              fontSize: size === 'small' ? 12 : 14,
              color: '#8c8c8c',
            }}
          >
            / {epsilon.toFixed(3)}
          </span>
        </div>
      </div>

      {showProgress && (
        <Tooltip
          title={`已消耗 ${consumptionRate.toFixed(1)}%，剩余 ${remainingRate.toFixed(1)}%`}
        >
          <Progress
            percent={consumptionRate}
            size={s.progressHeight}
            showInfo={size !== 'small'}
            strokeColor={config.color}
            trailColor="#d9d9d9"
            format={(percent) => `${percent?.toFixed(1)}%`}
          />
        </Tooltip>
      )}

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: size === 'small' ? 6 : 10,
          fontSize: size === 'small' ? 11 : 12,
          color: '#8c8c8c',
        }}
      >
        <Tooltip title="隐私失败概率">
          <span>δ = {delta.toExponential(2)}</span>
        </Tooltip>
        <span>剩余: {(epsilon - epsilonConsumed).toFixed(3)}</span>
      </div>
    </Card>
  );
};

export default PrivacyBudgetCard;
