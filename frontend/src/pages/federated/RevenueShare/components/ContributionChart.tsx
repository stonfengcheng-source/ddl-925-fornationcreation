import React, { useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Radio } from 'antd';
import { NodeContribution } from '../../../../types/training';

interface ContributionChartProps {
  contributions: NodeContribution[];
}

type ChartType = 'pie' | 'bar' | 'radar';

const ContributionChart: React.FC<ContributionChartProps> = ({
  contributions,
}) => {
  const [chartType, setChartType] = useState<ChartType>('pie');

  // 饼图配置 - 按奖励分配比例
  const pieOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: ¥{c} ({d}%)',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: {
        color: '#333',
      },
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'center',
    },
    series: [
      {
        name: '奖励分配',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n¥{c}',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        data: contributions.map((node) => ({
          value: node.rewardAmount,
          name: node.nodeName,
        })),
      },
    ],
    color: ['#1890ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1', '#13c2c2'],
  };

  // 柱状图配置 - 各维度得分
  const barOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: {
        color: '#333',
      },
    },
    legend: {
      data: ['数据质量', '数据量', '计算能力', '及时性', '综合得分'],
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
      data: contributions.map((n) => n.nodeName),
      axisLabel: {
        interval: 0,
        rotate: 15,
      },
    },
    yAxis: {
      type: 'value',
      max: 100,
      axisLabel: {
        formatter: '{value}分',
      },
    },
    series: [
      {
        name: '数据质量',
        type: 'bar',
        data: contributions.map((n) => n.dataQualityScore),
        itemStyle: { color: '#52c41a' },
      },
      {
        name: '数据量',
        type: 'bar',
        data: contributions.map((n) => n.dataQuantityScore),
        itemStyle: { color: '#1890ff' },
      },
      {
        name: '计算能力',
        type: 'bar',
        data: contributions.map((n) => n.computationScore),
        itemStyle: { color: '#722ed1' },
      },
      {
        name: '及时性',
        type: 'bar',
        data: contributions.map((n) => n.timelinessScore),
        itemStyle: { color: '#faad14' },
      },
      {
        name: '综合得分',
        type: 'line',
        data: contributions.map((n) => n.overallScore),
        itemStyle: { color: '#ff4d4f' },
        lineStyle: { width: 3 },
        symbol: 'circle',
        symbolSize: 8,
      },
    ],
  };

  // 雷达图配置 - 平均分
  const radarOption = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e8e8e8',
      borderWidth: 1,
      textStyle: {
        color: '#333',
      },
    },
    legend: {
      data: ['平均得分'],
      bottom: 0,
    },
    radar: {
      indicator: [
        { name: '数据质量', max: 100 },
        { name: '数据量', max: 100 },
        { name: '计算能力', max: 100 },
        { name: '及时性', max: 100 },
      ],
      shape: 'polygon',
      splitNumber: 5,
      axisName: {
        color: '#666',
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(24, 144, 255, 0.2)',
        },
      },
      splitArea: {
        areaStyle: {
          color: ['rgba(24, 144, 255, 0.05)', 'rgba(24, 144, 255, 0.1)'],
        },
      },
    },
    series: [
      {
        name: '贡献度分析',
        type: 'radar',
        data: [
          {
            value: [
              contributions.reduce((sum, n) => sum + n.dataQualityScore, 0) /
                contributions.length,
              contributions.reduce((sum, n) => sum + n.dataQuantityScore, 0) /
                contributions.length,
              contributions.reduce((sum, n) => sum + n.computationScore, 0) /
                contributions.length,
              contributions.reduce((sum, n) => sum + n.timelinessScore, 0) /
                contributions.length,
            ],
            name: '平均得分',
            areaStyle: {
              color: 'rgba(24, 144, 255, 0.3)',
            },
            lineStyle: {
              color: '#1890ff',
              width: 2,
            },
            itemStyle: {
              color: '#1890ff',
            },
          },
        ],
      },
    ],
  };

  const getOption = () => {
    switch (chartType) {
      case 'pie':
        return pieOption;
      case 'bar':
        return barOption;
      case 'radar':
        return radarOption;
      default:
        return pieOption;
    }
  };

  // 计算统计数据
  const totalReward = contributions.reduce((sum, n) => sum + n.rewardAmount, 0);
  const avgContribution =
    contributions.reduce((sum, n) => sum + n.overallScore, 0) /
    contributions.length;

  return (
    <div className="w-full">
      {/* 图表类型切换 */}
      <div className="flex justify-end mb-4">
        <Radio.Group
          value={chartType}
          onChange={(e) => setChartType(e.target.value)}
          optionType="button"
          buttonStyle="solid"
          size="small"
        >
          <Radio.Button value="pie">饼图</Radio.Button>
          <Radio.Button value="bar">柱状图</Radio.Button>
          <Radio.Button value="radar">雷达图</Radio.Button>
        </Radio.Group>
      </div>

      <ReactECharts
        option={getOption()}
        style={{ height: '350px', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
      />

      {/* 统计摘要 */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-gray-100">
        <div className="text-center">
          <div className="text-sm text-gray-500">总奖励</div>
          <div className="text-lg font-semibold text-blue-600">
            ¥{totalReward.toLocaleString()}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">平均贡献度</div>
          <div className="text-lg font-semibold text-green-600">
            {avgContribution.toFixed(1)}
          </div>
        </div>
        <div className="text-center">
          <div className="text-sm text-gray-500">参与节点</div>
          <div className="text-lg font-semibold text-purple-600">
            {contributions.length} 个
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContributionChart;
