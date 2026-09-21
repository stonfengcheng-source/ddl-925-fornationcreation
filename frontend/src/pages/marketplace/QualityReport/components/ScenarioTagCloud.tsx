import React from 'react';
import { Card, Tag, Typography, Space, Divider } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

const { Title } = Typography;

interface Props {
  suitableScenarios: string[];
  unsuitableScenarios: string[];
}

const ScenarioTagCloud: React.FC<Props> = ({ suitableScenarios, unsuitableScenarios }) => {
  return (
    <Card bordered={false} className="shadow-sm mt-4">
      <Space split={<Divider type="vertical" />} className="w-full justify-around" size="large">
        
        {/* 适用场景 */}
        <div className="flex-1">
          <Title level={5} className="mb-4 text-green-600 flex items-center gap-2">
            <CheckCircleOutlined /> 适用场景
          </Title>
          <div className="flex flex-wrap gap-2">
            {suitableScenarios.map(tag => (
              <Tag key={tag} color="success" className="px-3 py-1 text-sm">
                {tag}
              </Tag>
            ))}
          </div>
        </div>

        {/* 不适用场景 */}
        <div className="flex-1">
          <Title level={5} className="mb-4 text-red-500 flex items-center gap-2">
            <CloseCircleOutlined /> 不建议场景
          </Title>
          <div className="flex flex-wrap gap-2">
            {unsuitableScenarios.map(tag => (
              <Tag key={tag} color="error" className="px-3 py-1 text-sm">
                {tag}
              </Tag>
            ))}
          </div>
        </div>

      </Space>
    </Card>
  );
};

export default ScenarioTagCloud;
