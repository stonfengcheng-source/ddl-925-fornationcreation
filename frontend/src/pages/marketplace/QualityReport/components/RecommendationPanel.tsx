import React from 'react';
import { Card, List, Typography } from 'antd';
import { BulbOutlined } from '@ant-design/icons';

const { Text } = Typography;

interface Props {
  recommendations: string[];
}

const RecommendationPanel: React.FC<Props> = ({ recommendations }) => {
  return (
    <Card 
      title={
        <div className="flex items-center gap-2 text-blue-600">
          <BulbOutlined /> 优化建议
        </div>
      }
      bordered={false} 
      className="shadow-sm mt-4 border-l-4 border-l-blue-500"
    >
      <List
        dataSource={recommendations}
        renderItem={(item, index) => (
          <List.Item>
            <Text>
              <span className="font-bold mr-2 text-blue-500">#{index + 1}</span>
              {item}
            </Text>
          </List.Item>
        )}
      />
    </Card>
  );
};

export default RecommendationPanel;
