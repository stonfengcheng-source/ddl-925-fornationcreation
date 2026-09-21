import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Card } from 'antd';

interface Props {
  layerScores: {
    layer1: number;
    layer2: number;
    layer3: number;
    layer4: number;
    layer5: number;
  };
}

const LayerRadarChart: React.FC<Props> = ({ layerScores }) => {
  const option = {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      confine: true,
      formatter: (params: any) => {
        // Only handle tooltip for the transparent bar series (which has index 2)
        // or check if it's the bar series by name or type if needed.
        // But since we disable tooltip for others, this is fine.

        const layerNames = [
          'Layer 1 - 基础统计量',
          'Layer 2 - 特征相关性',
          'Layer 3 - 分布拟合',
          'Layer 4 - 高阶交互',
          'Layer 5 - 因果结构'
        ];

        const scores = [
          layerScores.layer1,
          layerScores.layer2,
          layerScores.layer3,
          layerScores.layer4,
          layerScores.layer5
        ];

        // params.dataIndex corresponds to the sector index (0-4)
        const index = params.dataIndex;
        const score = scores[index];

        return `<strong>${layerNames[index]}</strong><br/>评分: ${score}分`;
      }
    },
    legend: {
      bottom: 10,
      left: 'center',
      data: ['质量评分'],
      textStyle: { fontSize: 14 }
    },
    radar: {
      indicator: [
        { name: 'Layer 1\n基础统计量', max: 100 },
        { name: 'Layer 2\n特征相关性', max: 100 },
        { name: 'Layer 3\n分布拟合', max: 100 },
        { name: 'Layer 4\n高阶交互', max: 100 },
        { name: 'Layer 5\n因果结构', max: 100 },
      ],
      shape: 'circle',
      splitNumber: 4,
      radius: '65%',
      center: ['50%', '50%'],
      axisName: {
        color: '#666',
        fontSize: 12
      },
      axisLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#ddd'
        }
      },
      splitArea: {
        show: true,
        areaStyle: {
          color: ['rgba(255,255,255,0.5)', 'rgba(240,240,240,0.5)']
        }
      }
    },
    polar: {
      radius: '65%',
      center: ['50%', '50%']
    },
    angleAxis: {
      type: 'category',
      data: ['Layer 1', 'Layer 2', 'Layer 3', 'Layer 4', 'Layer 5'],
      startAngle: 90,
      clockwise: true,
      show: false,
      min: 0,
      max: 5
    },
    radiusAxis: {
      min: 0,
      max: 100,
      show: false,
      axisLine: { show: false },
      axisLabel: { show: false }
    },
    series: [
      {
        type: 'radar',
        symbol: 'none',
        tooltip: {
          show: false
        },
        data: [
          {
            value: [
              layerScores.layer1,
              layerScores.layer2,
              layerScores.layer3,
              layerScores.layer4,
              layerScores.layer5,
            ],
            name: '质量评分',
            areaStyle: {
              color: 'rgba(24, 144, 255, 0.3)'
            },
            lineStyle: {
              color: '#1890ff',
              width: 2
            }
          }
        ]
      },
      {
        type: 'scatter',
        coordinateSystem: 'polar',
        name: '质量评分',
        symbol: 'circle',
        symbolSize: 8,
        itemStyle: {
          color: '#1890ff',
          borderColor: '#fff',
          borderWidth: 2
        },
        data: [
          { value: [layerScores.layer1, 0], name: 'Layer 1\n基础统计量' },
          { value: [layerScores.layer2, 1], name: 'Layer 2\n特征相关性' },
          { value: [layerScores.layer3, 2], name: 'Layer 3\n分布拟合' },
          { value: [layerScores.layer4, 3], name: 'Layer 4\n高阶交互' },
          { value: [layerScores.layer5, 4], name: 'Layer 5\n因果结构' }
        ],
        tooltip: {
          show: false // Disable scatter tooltip, let bar handle it
        }
      },
      {
        type: 'bar',
        coordinateSystem: 'polar',
        name: 'Interaction Layer',
        stack: 'interaction',
        data: [100, 100, 100, 100, 100], // Full radius to capture hover
        itemStyle: {
          color: 'rgba(0,0,0,0)' // Transparent
        },
        z: 10 // Ensure it's on top
      }
    ]
  };

  return (
    <Card title="五维质量雷达" bordered={false} className="h-full shadow-sm">
      <ReactECharts
        option={option}
        style={{ height: '300px', width: '100%' }}
        opts={{ renderer: 'svg' }}
      />
    </Card>
  );
};

export default LayerRadarChart;
