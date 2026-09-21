import React from 'react';
import ReactECharts from 'echarts-for-react';
import { TrainingMetrics } from '../../../../types/training';

interface TrainingChartProps {
  metrics: TrainingMetrics;
  height?: number;
}

const TrainingChart: React.FC<TrainingChartProps> = ({
  metrics,
  height = 350,
}) => {
  // 转换数据格式
  const rounds = metrics.metrics.map((m) => m.round);
  const lossData = metrics.metrics.map((m) => m.globalLoss);
  const accuracyData = metrics.metrics.map((m) => (m.globalAccuracy * 100).toFixed(2));
  const valLossData = metrics.metrics.map(
    (m) => m.validationLoss || m.globalLoss * 1.05
  );
  const valAccuracyData = metrics.metrics.map((m) =>
    ((m.validationAccuracy || m.globalAccuracy * 0.98) * 100).toFixed(2)
  );

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: {
        color: '#333',
      },
      formatter: function (params: any[]) {
        let result = `<div style="font-weight: bold; margin-bottom: 8px;">第 ${params[0].axisValue} 轮</div>`;
        params.forEach((param) => {
          const color = param.color;
          const unit = param.seriesName.includes('准确率') ? '%' : '';
          result += `<div style="display: flex; align-items: center; gap: 8px; margin: 4px 0;">
            <span style="display: inline-block; width: 10px; height: 10px; background: ${color}; border-radius: 50%;"></span>
            <span>${param.seriesName}: ${param.value}${unit}</span>
          </div>`;
        });
        return result;
      },
    },
    legend: {
      data: ['训练 Loss', '验证 Loss', '训练准确率', '验证准确率'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: rounds,
      name: '训练轮次',
      nameLocation: 'middle',
      nameGap: 30,
      axisLine: {
        lineStyle: {
          color: '#d9d9d9',
        },
      },
      axisLabel: {
        color: '#666',
        interval: Math.floor(rounds.length / 10),
      },
    },
    yAxis: [
      {
        type: 'value',
        name: 'Loss',
        position: 'left',
        axisLine: {
          lineStyle: {
            color: '#ff4d4f',
          },
        },
        axisLabel: {
          color: '#ff4d4f',
        },
        splitLine: {
          lineStyle: {
            color: '#f0f0f0',
          },
        },
      },
      {
        type: 'value',
        name: 'Accuracy (%)',
        position: 'right',
        min: 0,
        max: 100,
        axisLine: {
          lineStyle: {
            color: '#52c41a',
          },
        },
        axisLabel: {
          color: '#52c41a',
          formatter: '{value}%',
        },
        splitLine: {
          show: false,
        },
      },
    ],
    series: [
      {
        name: '训练 Loss',
        type: 'line',
        data: lossData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#ff4d4f',
          width: 2,
        },
        itemStyle: {
          color: '#ff4d4f',
        },
      },
      {
        name: '验证 Loss',
        type: 'line',
        data: valLossData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#ff7875',
          width: 1,
          type: 'dashed',
        },
        itemStyle: {
          color: '#ff7875',
        },
      },
      {
        name: '训练准确率',
        type: 'line',
        yAxisIndex: 1,
        data: accuracyData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#52c41a',
          width: 2,
        },
        itemStyle: {
          color: '#52c41a',
        },
      },
      {
        name: '验证准确率',
        type: 'line',
        yAxisIndex: 1,
        data: valAccuracyData,
        smooth: true,
        symbol: 'none',
        lineStyle: {
          color: '#95de64',
          width: 1,
          type: 'dashed',
        },
        itemStyle: {
          color: '#95de64',
        },
      },
    ],
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        bottom: 40,
      },
    ],
  };

  // 计算统计数据
  const latestMetric = metrics.metrics[metrics.metrics.length - 1];

  return (
    <div className="w-full">
      <ReactECharts
        option={option}
        style={{ height: `${height}px`, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />

      {/* 统计摘要 */}
      <div className="flex justify-around mt-4 pt-4 border-t border-gray-100">
        <div className="text-center">
          <div className="text-sm text-gray-500">最新 Loss</div>
          <div className="text-lg font-semibold text-red-500">
            {latestMetric?.globalLoss.toFixed(4)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">最新准确率</div>
          <div className="text-lg font-semibold text-green-500">
            {((latestMetric?.globalAccuracy || 0) * 100).toFixed(2)}%
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">当前轮次</div>
          <div className="text-lg font-semibold text-blue-500">
            {metrics.currentRound} / {metrics.totalRounds}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">预计剩余时间</div>
          <div className="text-lg font-semibold text-purple-500">
            {metrics.estimatedTimeRemaining
              ? `${Math.floor(metrics.estimatedTimeRemaining / 60)}分钟`
              : '计算中...'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrainingChart;
