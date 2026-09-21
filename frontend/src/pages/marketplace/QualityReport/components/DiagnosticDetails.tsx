import React from 'react';
import { Collapse, Card, Descriptions, Table, Progress, List, Tag } from 'antd';
import { CaretRightOutlined } from '@ant-design/icons';
import { QualityReport } from '../../../../types/quality';
import Layer2Report from './Layer2Report';

const { Panel } = Collapse;

interface Props {
  details: QualityReport['diagnosticDetails'];
}

const DiagnosticDetails: React.FC<Props> = ({ details }) => {
  
  // Layer 1 内容渲染
  const renderLayer1 = () => (
    <div>
      <Descriptions column={3} bordered size="small" className="mb-4">
        <Descriptions.Item label="样本量">{details.layer1.sampleSize}</Descriptions.Item>
        <Descriptions.Item label="缺失率">{(details.layer1.missingRate * 100).toFixed(2)}%</Descriptions.Item>
        <Descriptions.Item label="异常值比例">{(details.layer1.outlierRate * 100).toFixed(2)}%</Descriptions.Item>
      </Descriptions>
      <Table 
        dataSource={details.layer1.featureStats}
        rowKey="name"
        size="small"
        pagination={false}
        columns={[
          { title: '特征名', dataIndex: 'name' },
          { title: '均值', dataIndex: 'mean' },
          { title: '标准差', dataIndex: 'std' },
          { title: '最小值', dataIndex: 'min' },
          { title: '最大值', dataIndex: 'max' },
        ]}
      />
    </div>
  );

  // Layer 3 内容渲染
  const renderLayer3 = () => (
    <Table 
      dataSource={details.layer3.distributionFits}
      rowKey="feature"
      size="small"
      columns={[
        { title: '特征', dataIndex: 'feature' },
        { title: '最佳拟合分布', dataIndex: 'bestFit', render: (text) => <Tag color="blue">{text}</Tag> },
        { title: 'KS检验 P值', dataIndex: 'pValue' },
        { 
          title: '是否正态', 
          dataIndex: 'isNormal', 
          render: (val) => val ? <Tag color="green">是</Tag> : <Tag color="orange">否</Tag> 
        },
      ]}
    />
  );

  // Layer 4 内容渲染
  const renderLayer4 = () => (
    <List
      dataSource={details.layer4.interactionEffects}
      renderItem={(item) => (
        <List.Item>
          <div className="w-full flex items-center justify-between">
            <div className="w-1/3">
              <Tag>{item.features[0]}</Tag> x <Tag>{item.features[1]}</Tag>
            </div>
            <div className="w-1/3 px-4">
              <Progress percent={item.strength * 100} size="small" showInfo={false} />
            </div>
            <div className="w-1/3 text-right">
              {item.type === 'synergy' ? 
                <Tag color="purple">协同效应 (Synergy)</Tag> : 
                <Tag color="cyan">冗余效应 (Redundancy)</Tag>
              }
              <span className="ml-2 text-gray-500">{item.strength.toFixed(2)}</span>
            </div>
          </div>
        </List.Item>
      )}
    />
  );

  return (
    <Card title="详细诊断报告" bordered={false} className="shadow-sm mt-4">
      <Collapse 
        defaultActiveKey={['layer1']} 
        expandIcon={({ isActive }) => <CaretRightOutlined rotate={isActive ? 90 : 0} />}
        className="bg-white"
      >
        <Panel header="Layer 1 - 基础统计量 (Basic Statistics)" key="layer1">
          {renderLayer1()}
        </Panel>
        
        <Panel header="Layer 2 - 特征相关性 (Feature Correlation)" key="layer2">
          <Layer2Report data={details.layer2} />
        </Panel>
        
        <Panel header="Layer 3 - 分布拟合 (Distribution Fit)" key="layer3">
          {renderLayer3()}
        </Panel>
        
        <Panel header="Layer 4 - 高阶交互 (Higher-order Interactions)" key="layer4">
          {renderLayer4()}
        </Panel>
      </Collapse>
    </Card>
  );
};

export default DiagnosticDetails;
