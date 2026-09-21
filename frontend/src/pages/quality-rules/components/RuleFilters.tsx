import React from 'react';
import { Input, Select, Button, Space } from 'antd';
import { Search, X } from 'lucide-react';
import type { RuleType, RuleStatus } from '@/types/qualityRule';
import styles from '../index.module.less';

const { Option } = Select;

interface RuleFiltersProps {
  searchText: string;
  onSearchChange: (value: string) => void;
  typeFilter: RuleType | 'all';
  onTypeChange: (value: RuleType | 'all') => void;
  statusFilter: RuleStatus | 'all';
  onStatusChange: (value: RuleStatus | 'all') => void;
  onClearFilters: () => void;
  hasActiveFilters: boolean;
}

const ruleTypeOptions: { value: RuleType | 'all'; label: string }[] = [
  { value: 'all', label: '全部类型' },
  { value: 'format', label: '格式验证' },
  { value: 'range', label: '范围验证' },
  { value: 'logic', label: '逻辑验证' },
  { value: 'custom', label: '自定义' },
];

const ruleStatusOptions: { value: RuleStatus | 'all'; label: string }[] = [
  { value: 'all', label: '全部状态' },
  { value: 'active', label: '已启用' },
  { value: 'draft', label: '草稿' },
  { value: 'disabled', label: '已禁用' },
];

export const RuleFilters: React.FC<RuleFiltersProps> = ({
  searchText,
  onSearchChange,
  typeFilter,
  onTypeChange,
  statusFilter,
  onStatusChange,
  onClearFilters,
  hasActiveFilters,
}) => {
  return (
    <div className={styles.filterBar}>
      <div className={styles.filterLeft}>
        <Space size="middle">
          <Input
            placeholder="搜索规则名称..."
            value={searchText}
            onChange={(e) => onSearchChange(e.target.value)}
            prefix={<Search size={16} />}
            allowClear
            style={{ width: 240 }}
          />
          <Select
            placeholder="规则类型"
            value={typeFilter}
            onChange={onTypeChange}
            style={{ width: 140 }}
          >
            {ruleTypeOptions.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
          <Select
            placeholder="规则状态"
            value={statusFilter}
            onChange={onStatusChange}
            style={{ width: 140 }}
          >
            {ruleStatusOptions.map((opt) => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
        </Space>
      </div>
      <div className={styles.filterRight}>
        {hasActiveFilters && (
          <Button
            icon={<X size={14} />}
            onClick={onClearFilters}
            type="link"
          >
            清除筛选
          </Button>
        )}
      </div>
    </div>
  );
};

export default RuleFilters;
