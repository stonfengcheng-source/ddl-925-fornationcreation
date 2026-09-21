import React from 'react';
import { Card, Statistic } from 'antd';
import { LucideIcon } from 'lucide-react';
import styles from '../index.module.less';

interface StatsCardProps {
  title: string;
  value: number;
  icon: LucideIcon;
  color: 'blue' | 'green' | 'orange' | 'red' | 'purple';
  suffix?: string;
}

const colorMap: Record<string, string> = {
  blue: '#3b82f6',
  green: '#10b981',
  orange: '#f59e0b',
  red: '#ef4444',
  purple: '#8b5cf6',
};

export const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon: Icon,
  color,
  suffix,
}) => {
  return (
    <Card bordered={false} className={styles.statsCard}>
      <div className={styles.statsCardContent}>
        <div
          className={styles.statsIcon}
          style={{ backgroundColor: `${colorMap[color]}15`, color: colorMap[color] }}
        >
          <Icon size={24} />
        </div>
        <div className={styles.statsInfo}>
          <div className={styles.statsTitle}>{title}</div>
          <div className={styles.statsValue} style={{ color: colorMap[color] }}>
            <Statistic value={value} suffix={suffix} />
          </div>
        </div>
      </div>
    </Card>
  );
};

export default StatsCard;
