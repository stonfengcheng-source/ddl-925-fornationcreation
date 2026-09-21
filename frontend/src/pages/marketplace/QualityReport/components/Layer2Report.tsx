import React from 'react';
import ReactECharts from 'echarts-for-react';
import { Table, Row, Col, Typography } from 'antd';
import { Layer2Details } from '../../../../types/quality';

const { Text } = Typography;

interface Props {
  data: Layer2Details;
}

const Layer2Report: React.FC<Props> = ({ data }) => {
  const { correlationMatrix, significantPairs, featureNames = [] } = data;

  // 构造热力图数据 [x, y, value]
  const heatmapData = correlationMatrix.flatMap((row, i) =>
    row.map((val, j) => [i, j, val.toFixed(2)])
  );

  const option = {
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        const xName = featureNames[params.data[0]] || `F${params.data[0]}`;
        const yName = featureNames[params.data[1]] || `F${params.data[1]}`;
        return `${xName} vs ${yName}: ${params.data[2]}`;
      }
    },
    grid: {
      top: '10%',
      bottom: '15%',
      left: '10%',
      right: '10%'
    },
    xAxis: {
      type: 'category',
      data: featureNames,
      splitArea: { show: true }
    },
    yAxis: {
      type: 'category',
      data: featureNames,
      splitArea: { show: true }
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: '0%',
      inRange: {
        color: ['#4575b4', '#91bfdb', '#e0f3f8', '#ffffbf', '#fee090', '#fc8d59', '#d73027']
      }
    },
    series: [
      {
        name: 'Correlation',
        type: 'heatmap',
        data: heatmapData,
        label: {
          show: true
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };

  const columns = [
    { title: '特征 1', dataIndex: 'feature1', key: 'feature1' },
    { title: '特征 2', dataIndex: 'feature2', key: 'feature2' },
    { 
      title: '相关系数', 
      dataIndex: 'correlation', 
      key: 'correlation',
      render: (val: number) => (
        <Text type={Math.abs(val) > 0.7 ? 'danger' : undefined} strong={Math.abs(val) > 0.7}>
          {val.toFixed(2)}
        </Text>
      )
    },
    { 
      title: 'P值', 
      dataIndex: 'pValue', 
      key: 'pValue',
      render: (val: number) => val < 0.05 ? '< 0.05' : val.toFixed(3)
    },
  ];

  return (
    <Row gutter={24}>
      <Col span={12}>
        <div className="h-full">
          <ReactECharts option={option} style={{ height: '350px' }} />
        </div>
      </Col>
      <Col span={12}>
        <Table 
          columns={columns} 
          dataSource={significantPairs} 
          rowKey={(record) => `${record.feature1}-${record.feature2}`}
          size="small"
          pagination={false}
          scroll={{ y: 300 }}
          title={() => '显著相关特征对'}
        />
      </Col>
    </Row>
  );
};

export default Layer2Report;
