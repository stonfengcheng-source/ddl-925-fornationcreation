import React from 'react';
import { Card, Typography, Tag, Flex } from 'antd';

const { Title, Text } = Typography;

interface Props {
  score: number;
  rating: 'excellent' | 'good' | 'fair' | 'poor';
}

const ratingConfig = {
  excellent: { color: '#52c41a', text: '优秀', bg: '#f6ffed' },
  good: { color: '#1890ff', text: '良好', bg: '#e6f7ff' },
  fair: { color: '#faad14', text: '一般', bg: '#fffbe6' },
  poor: { color: '#ff4d4f', text: '较差', bg: '#fff1f0' },
};

const OverallScoreCard: React.FC<Props> = ({ score, rating }) => {
  const config = ratingConfig[rating];

  return (
    <Card 
      title="综合质量评分" 
      bordered={false} 
      className="h-full shadow-sm"
      bodyStyle={{ padding: '24px', height: 'calc(100% - 57px)' }}
    >
      <Flex vertical align="center" justify="center" gap={16} className="h-full">
        <div className="relative flex items-center justify-center">
          <Title level={1} style={{ margin: 0, fontSize: '4.5rem', color: config.color }}>
            {score}
          </Title>
        </div>
        
        <Tag 
          color={config.color} 
          style={{ 
            fontSize: '1.2rem', 
            padding: '4px 24px', 
            borderRadius: '20px',
            lineHeight: '1.8'
          }}
        >
          {config.text}
        </Tag>

        <Text type="secondary">基于 5 个维度的综合评估</Text>
      </Flex>
    </Card>
  );
};

export default OverallScoreCard;
