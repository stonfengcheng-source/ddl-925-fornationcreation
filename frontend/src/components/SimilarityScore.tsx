/**
 * 相似度分数可视化组件
 * 展示总分环形图和三个维度的条形图
 */
import React from 'react';
import { Progress, Tooltip } from 'antd';
import type { MatchScore } from '@/types/training';

interface SimilarityScoreProps {
  scores: MatchScore;
  size?: 'small' | 'medium' | 'large';
  showDetails?: boolean;
}

const sizeConfig = {
  small: {
    strokeWidth: 6,
    width: 60,
    barHeight: 4,
    fontSize: 'text-xs',
  },
  medium: {
    strokeWidth: 8,
    width: 80,
    barHeight: 6,
    fontSize: 'text-sm',
  },
  large: {
    strokeWidth: 10,
    width: 100,
    barHeight: 8,
    fontSize: 'text-base',
  },
};

/**
 * 将分数转换为颜色
 * 0-0.4: 红色 (低)
 * 0.4-0.7: 橙色 (中)
 * 0.7-1.0: 绿色 (高)
 */
const getScoreColor = (score: number): string => {
  if (score >= 0.7) return '#52c41a'; // success green
  if (score >= 0.4) return '#faad14'; // warning orange
  return '#f5222d'; // error red
};

/**
 * 将分数转换为百分比显示
 */
const formatPercent = (score: number): string => {
  return `${(score * 100).toFixed(0)}%`;
};

export const SimilarityScore: React.FC<SimilarityScoreProps> = ({
  scores,
  size = 'medium',
  showDetails = true,
}) => {
  const config = sizeConfig[size];

  // 总分提示内容
  const totalTooltip = (
    <div className="space-y-1">
      <div><strong>综合匹配度</strong></div>
      <div>语义相似度: {formatPercent(scores.semantic)}</div>
      <div>标签匹配: {formatPercent(scores.tag)}</div>
      <div>数据量匹配: {formatPercent(scores.quantity)}</div>
    </div>
  );

  return (
    <div className="flex items-center gap-4">
      {/* 总分环形图 */}
      <Tooltip title={totalTooltip} placement="top">
        <div className="flex flex-col items-center">
          <Progress
            type="circle"
            percent={scores.total * 100}
            strokeColor={getScoreColor(scores.total)}
            strokeWidth={config.strokeWidth}
            width={config.width}
            format={(percent) => (
              <span className={`${config.fontSize} font-semibold`}>
                {percent?.toFixed(0)}%
              </span>
            )}
          />
          <span className="text-xs text-gray-500 mt-1">匹配度</span>
        </div>
      </Tooltip>

      {/* 各维度详情 */}
      {showDetails && (
        <div className="flex-1 space-y-2">
          {/* 语义相似度 */}
          <Tooltip title="基于 AI 语义理解的相似度" placement="top">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-12">语义</span>
              <Progress
                percent={scores.semantic * 100}
                strokeColor="#1890ff"
                strokeWidth={config.barHeight}
                showInfo={false}
                className="flex-1"
              />
              <span className={`${config.fontSize} text-gray-600 w-10 text-right`}>
                {formatPercent(scores.semantic)}
              </span>
            </div>
          </Tooltip>

          {/* 标签匹配 */}
          <Tooltip title="任务标签与数据集标签的重叠度" placement="top">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-12">标签</span>
              <Progress
                percent={scores.tag * 100}
                strokeColor="#52c41a"
                strokeWidth={config.barHeight}
                showInfo={false}
                className="flex-1"
              />
              <span className={`${config.fontSize} text-gray-600 w-10 text-right`}>
                {formatPercent(scores.tag)}
              </span>
            </div>
          </Tooltip>

          {/* 数据量匹配 */}
          <Tooltip title="数据量是否满足任务要求" placement="top">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-12">数据</span>
              <Progress
                percent={scores.quantity * 100}
                strokeColor="#faad14"
                strokeWidth={config.barHeight}
                showInfo={false}
                className="flex-1"
              />
              <span className={`${config.fontSize} text-gray-600 w-10 text-right`}>
                {formatPercent(scores.quantity)}
              </span>
            </div>
          </Tooltip>
        </div>
      )}
    </div>
  );
};

export default SimilarityScore;
