import React from 'react';
import { Table, Tag, Space, Button, Dropdown, Modal, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  Edit,
  MoreVertical,
  Trash2,
  Power,
  PowerOff,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react';
import type { QualityRule, RuleType, RuleStatus } from '@/types/qualityRule';
import styles from '../index.module.less';

interface RuleTableProps {
  data: QualityRule[];
  loading: boolean;
  selectedRowKeys: React.Key[];
  onSelectionChange: (selectedRowKeys: React.Key[], selectedRows: QualityRule[]) => void;
  onEdit: (rule: QualityRule) => void;
  onToggleStatus: (rule: QualityRule) => void;
  onDelete: (rule: QualityRule) => void;
  onViewDetail: (rule: QualityRule) => void;
}

const ruleTypeMap: Record<RuleType, { color: string; text: string }> = {
  format: { color: 'blue', text: '格式验证' },
  range: { color: 'green', text: '范围验证' },
  logic: { color: 'purple', text: '逻辑验证' },
  custom: { color: 'orange', text: '自定义' },
};

const ruleStatusMap: Record<RuleStatus, { color: string; text: string; icon: React.ElementType }> = {
  active: { color: 'success', text: '已启用', icon: CheckCircle },
  draft: { color: 'warning', text: '草稿', icon: Clock },
  disabled: { color: 'default', text: '已禁用', icon: XCircle },
};

export const RuleTable: React.FC<RuleTableProps> = ({
  data,
  loading,
  selectedRowKeys,
  onSelectionChange,
  onEdit,
  onToggleStatus,
  onDelete,
  onViewDetail,
}) => {
  const handleDelete = (rule: QualityRule) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除规则"${rule.name}"吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => onDelete(rule),
    });
  };

  const columns: ColumnsType<QualityRule> = [
    {
      title: '规则名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: QualityRule) => (
        <div className={styles.ruleNameCell}>
          <div className={styles.ruleName} onClick={() => onViewDetail(record)}>
            {text}
          </div>
          <Tooltip title={record.description}>
            <div className={styles.ruleDescription}>{record.description}</div>
          </Tooltip>
        </div>
      ),
    },
    {
      title: '规则类型',
      dataIndex: 'ruleType',
      key: 'ruleType',
      width: 120,
      render: (type: RuleType) => (
        <Tag color={ruleTypeMap[type].color}>{ruleTypeMap[type].text}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: RuleStatus) => {
        const config = ruleStatusMap[status];
        const Icon = config.icon;
        return (
          <div className={styles.statusCell}>
            <Icon size={14} className={styles.statusIcon} />
            <span className={`${styles.statusText} ${styles[status]}`}>{config.text}</span>
          </div>
        );
      },
    },
    {
      title: '字段数',
      dataIndex: 'fieldDefinitions',
      key: 'fieldCount',
      width: 90,
      align: 'center',
      render: (fields?: { length: number }[]) => fields?.length ?? 0,
    },
    {
      title: '测试用例',
      dataIndex: 'testCases',
      key: 'testCaseCount',
      width: 90,
      align: 'center',
      render: (testCases?: { length: number }[]) => testCases?.length ?? 0,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 180,
      render: (date: string) => {
        const d = new Date(date);
        return d.toLocaleString('zh-CN', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_: unknown, record: QualityRule) => {
        const menuItems = [
          {
            key: 'edit',
            icon: <Edit size={14} />,
            label: '编辑',
            onClick: () => onEdit(record),
          },
          {
            key: 'toggle',
            icon: record.status === 'active' ? <PowerOff size={14} /> : <Power size={14} />,
            label: record.status === 'active' ? '禁用' : '启用',
            onClick: () => onToggleStatus(record),
          },
          {
            key: 'delete',
            icon: <Trash2 size={14} />,
            label: '删除',
            danger: true,
            onClick: () => handleDelete(record),
          },
        ];

        return (
          <Space size="small">
            <Button
              type="link"
              size="small"
              icon={<Eye size={14} />}
              onClick={() => onViewDetail(record)}
            >
              详情
            </Button>
            <Dropdown
              menu={{ items: menuItems }}
              placement="bottomRight"
              trigger={['click']}
            >
              <Button
                type="text"
                size="small"
                icon={<MoreVertical size={14} />}
              />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  const rowSelection = {
    selectedRowKeys,
    onChange: onSelectionChange,
  };

  return (
    <Table
      rowSelection={rowSelection}
      columns={columns}
      dataSource={data}
      rowKey="id"
      loading={loading}
      pagination={{
        pageSize: 10,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 条规则`,
        pageSizeOptions: ['10', '20', '50'],
      }}
      scroll={{ x: 900 }}
      className={styles.ruleTable}
    />
  );
};

export default RuleTable;
