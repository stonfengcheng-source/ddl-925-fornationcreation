import React from 'react';
import ReactECharts from 'echarts-for-react';
import type { PrivacyBudgetTrendChartProps } from '@/types/training';

/**
 * PrivacyBudgetTrendChart 组件
 * 使用ECharts展示隐私预算消耗趋势
 * 面积图展示累计消耗，显示总预算阈值参考线
 */
const PrivacyBudgetTrendChart: React.FC<PrivacyBudgetTrendChartProps> = ({
  data,
  totalBudget,
  height = 300,
  title = '隐私预算消耗趋势',
}) => {
  // 处理数据
  const rounds = data.map((item) => `第${item.round}轮`);
  const cumulativeData = data.map((item) => item.epsilonCumulative);
  const roundConsumptionData = data.map((item) => item.epsilonConsumed);

  // 计算当前消耗和剩余
  const currentConsumption = data.length > 0 ? data[data.length - 1].epsilonCumulative : 0;
  const remainingBudget = Math.max(0, totalBudget - currentConsumption);
  const consumptionRate = totalBudget > 0 ? (currentConsumption / totalBudget) * 100 : 0;

  const option = {
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 500,
        color: '#262626',
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        crossStyle: {
          color: '#999',
        },
      },
      formatter: function (params: any[]) {
        const round = params[0].axisValue;
        const cumulative = params.find((p) => p.seriesName === '累计消耗')?.value || 0;
        const current = params.find((p) => p.seriesName === '本轮消耗')?.value || 0;
        return `
          <div style="padding: 8px;">
            <div style="font-weight: 600; margin-bottom: 8px;">${round}</div>
            <div style="color: #fa8c16; margin-bottom: 4px;">
              ● 累计消耗: ε = ${cumulative.toFixed(4)}
            </div>
            <div style="color: #1890ff; margin-bottom: 4px;">
              ● 本轮消耗: ε = ${current.toFixed(4)}
            </div>
            <div style="color: #8c8c8c; font-size: 12px;">
              剩余预算: ε = ${Math.max(0, totalBudget - cumulative).toFixed(4)}
            </div>
          </div>
        `;
      },
    },
    legend: {
      data: ['累计消耗', '本轮消耗', '总预算阈值'],
      bottom: 0,
      itemGap: 20,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: rounds,
      axisPointer: {
        type: 'shadow',
      },
      axisLabel: {
        interval: Math.floor(rounds.length / 10),
        rotate: rounds.length > 20 ? 45 : 0,
        color: '#8c8c8c',
      },
      axisLine: {
        lineStyle: {
          color: '#d9d9d9',
        },
      },
    },
    yAxis: {
      type: 'value',
      name: '隐私预算 (ε)',
      nameTextStyle: {
        color: '#8c8c8c',
        padding: [0, 0, 0, 50],
      },
      axisLabel: {
        formatter: '{value}',
        color: '#8c8c8c',
      },
      axisLine: {
        lineStyle: {
          color: '#d9d9d9',
        },
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed',
        },
      },
    },
    series: [
      {
        name: '累计消耗',
        type: 'line',
        data: cumulativeData,
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#fa8c16',
          width: 3,
        },
        itemStyle: {
          color: '#fa8c16',
        },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(250, 140, 22, 0.4)' },
              { offset: 1, color: 'rgba(250, 140, 22, 0.05)' },
            ],
          },
        },
        emphasis: {
          focus: 'series',
        },
      },
      {
        name: '本轮消耗',
        type: 'bar',
        data: roundConsumptionData,
        barWidth: '40%',
        itemStyle: {
          color: '#1890ff',
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: {
          focus: 'series',
        },
      },
      {
        name: '总预算阈值',
        type: 'line',
        data: new Array(data.length).fill(totalBudget),
        lineStyle: {
          color: '#f5222d',
          width: 2,
          type: 'dashed',
        },
        symbol: 'none',
        tooltip: {
          formatter: `总预算: ε = ${totalBudget}`,
        },
      },
    ],
    graphic: [
      {
        type: 'text',
        left: '3%',
        top: '8%',
        style: {
          text: `消耗率: ${consumptionRate.toFixed(1)}%`,
          fill: consumptionRate > 80 ? '#f5222d' : '#52c41a',
          fontSize: 14,
          fontWeight: 600,
        },
      },
      {
        type: 'text',
        right: '4%',
        top: '8%',
        style: {
          text: `剩余: ε ${remainingBudget.toFixed(3)}`,
          fill: remainingBudget < totalBudget * 0.2 ? '#f5222d' : '#262626',
          fontSize: 14,
          fontWeight: 600,
        },
      },
    ],
  };

  return (
    <div style={{ width: '100%', height }}>
      <ReactECharts
        option={option}
        style={{ width: '100%', height: '100%' }}
        opts={{ renderer: 'svg' }}
      />
    </div>
  );
};

export default PrivacyBudgetTrendChart;
