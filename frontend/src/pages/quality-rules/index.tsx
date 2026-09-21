import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Button, Space, Modal, message, Card, Typography, Empty } from 'antd';
import { Plus, Shield, FileCode, CheckCircle, XCircle, RefreshCw } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { QualityRule, RuleType, RuleStatus } from '@/types/qualityRule';
import { qualityRuleApi } from '@/services/api/qualityRule';
import { StatsCard } from './components/StatsCard';
import { RuleFilters } from './components/RuleFilters';
import { RuleTable } from './components/RuleTable';
import styles from './index.module.less';

const { Title, Text } = Typography;

const QualityRuleList: React.FC = () => {
  const navigate = useNavigate();

  // 数据状态
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [loading, setLoading] = useState(false);

  // 筛选状态
  const [searchText, setSearchText] = useState('');
  const [typeFilter, setTypeFilter] = useState<RuleType | 'all'>('all');
  const [statusFilter, setStatusFilter] = useState<RuleStatus | 'all'>('all');

  // 表格状态
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);

  // 加载数据
  const fetchRules = useCallback(async () => {
    setLoading(true);
    try {
      const data = await qualityRuleApi.getRules();
      setRules(data);
    } catch (error) {
      message.error('获取规则列表失败');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRules();
  }, [fetchRules]);

  // 统计数据
  const stats = useMemo(() => {
    const total = rules.length;
    const active = rules.filter((r) => r.status === 'active').length;
    const draft = rules.filter((r) => r.status === 'draft').length;
    const disabled = rules.filter((r) => r.status === 'disabled').length;
    return { total, active, draft, disabled };
  }, [rules]);

  // 筛选后的数据
  const filteredRules = useMemo(() => {
    return rules.filter((rule) => {
      // 搜索过滤
      if (searchText) {
        const searchLower = searchText.toLowerCase();
        const matchName = rule.name.toLowerCase().includes(searchLower);
        const matchDesc = rule.description.toLowerCase().includes(searchLower);
        if (!matchName && !matchDesc) return false;
      }

      // 类型过滤
      if (typeFilter !== 'all' && rule.ruleType !== typeFilter) {
        return false;
      }

      // 状态过滤
      if (statusFilter !== 'all' && rule.status !== statusFilter) {
        return false;
      }

      return true;
    });
  }, [rules, searchText, typeFilter, statusFilter]);

  // 是否有活跃筛选
  const hasActiveFilters = !!(searchText || typeFilter !== 'all' || statusFilter !== 'all');

  // 清除筛选
  const handleClearFilters = () => {
    setSearchText('');
    setTypeFilter('all');
    setStatusFilter('all');
  };

  // 新建规则
  const handleCreate = () => {
    navigate('/app/quality-rules/editor');
  };

  // 编辑规则
  const handleEdit = (rule: QualityRule) => {
    navigate(`/app/quality-rules/editor/${rule.id}`);
  };

  // 查看详情
  const handleViewDetail = (rule: QualityRule) => {
    navigate(`/app/quality-rules/editor/${rule.id}`);
  };

  // 切换状态
  const handleToggleStatus = async (rule: QualityRule) => {
    const newStatus = rule.status === 'active' ? 'disabled' : 'active';
    const actionText = newStatus === 'active' ? '启用' : '禁用';

    try {
      await qualityRuleApi.updateRule(rule.id, { status: newStatus });
      message.success(`规则"${rule.name}"已${actionText}`);
      // 乐观更新
      setRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, status: newStatus } : r))
      );
    } catch (error) {
      message.error(`${actionText}失败`);
      console.error(error);
    }
  };

  // 删除规则
  const handleDelete = async (rule: QualityRule) => {
    try {
      // TODO: 添加删除API
      // await qualityRuleApi.deleteRule(rule.id);
      message.success(`规则"${rule.name}"已删除`);
      // 乐观更新
      setRules((prev) => prev.filter((r) => r.id !== rule.id));
      // 清除已选中的行
      setSelectedRowKeys((prev) => prev.filter((key) => key !== rule.id));
    } catch (error) {
      message.error('删除失败');
      console.error(error);
    }
  };

  // 批量操作
  const handleBatchEnable = () => {
    Modal.confirm({
      title: '批量启用',
      content: `确定要启用选中的 ${selectedRowKeys.length} 个规则吗？`,
      onOk: async () => {
        try {
          // TODO: 添加批量更新API
          message.success('批量启用成功');
          setRules((prev) =>
            prev.map((r) =>
              selectedRowKeys.includes(r.id) ? { ...r, status: 'active' } : r
            )
          );
          setSelectedRowKeys([]);
        } catch (error) {
          message.error('批量启用失败');
        }
      },
    });
  };

  const handleBatchDisable = () => {
    Modal.confirm({
      title: '批量禁用',
      content: `确定要禁用选中的 ${selectedRowKeys.length} 个规则吗？`,
      onOk: async () => {
        try {
          message.success('批量禁用成功');
          setRules((prev) =>
            prev.map((r) =>
              selectedRowKeys.includes(r.id) ? { ...r, status: 'disabled' } : r
            )
          );
          setSelectedRowKeys([]);
        } catch (error) {
          message.error('批量禁用失败');
        }
      },
    });
  };

  const handleBatchDelete = () => {
    Modal.confirm({
      title: '批量删除',
      content: `确定要删除选中的 ${selectedRowKeys.length} 个规则吗？此操作不可恢复。`,
      okType: 'danger',
      onOk: async () => {
        try {
          message.success('批量删除成功');
          setRules((prev) =>
            prev.filter((r) => !selectedRowKeys.includes(r.id))
          );
          setSelectedRowKeys([]);
        } catch (error) {
          message.error('批量删除失败');
        }
      },
    });
  };

  return (
    <div className={styles.pageContainer}>
      {/* 页面头部 */}
      <div className={styles.pageHeader}>
        <div>
          <Title level={3} className={styles.pageTitle}>
            质量规则管理
          </Title>
          <Text type="secondary">
            管理数据质量验证规则，支持自然语言定义规则
          </Text>
        </div>
        <Space>
          <Button icon={<RefreshCw size={16} />} onClick={fetchRules}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<Plus size={16} />}
            onClick={handleCreate}
          >
            新建规则
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <div className={styles.statsRow}>
        <StatsCard
          title="总规则"
          value={stats.total}
          icon={Shield}
          color="blue"
        />
        <StatsCard
          title="已启用"
          value={stats.active}
          icon={CheckCircle}
          color="green"
        />
        <StatsCard
          title="草稿"
          value={stats.draft}
          icon={FileCode}
          color="orange"
        />
        <StatsCard
          title="已禁用"
          value={stats.disabled}
          icon={XCircle}
          color="red"
        />
      </div>

      {/* 筛选栏 */}
      <Card className={styles.filterCard}>
        <RuleFilters
          searchText={searchText}
          onSearchChange={setSearchText}
          typeFilter={typeFilter}
          onTypeChange={setTypeFilter}
          statusFilter={statusFilter}
          onStatusChange={setStatusFilter}
          onClearFilters={handleClearFilters}
          hasActiveFilters={hasActiveFilters}
        />
      </Card>

      {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <div className={styles.batchActionBar}>
          <span className={styles.batchText}>
            已选择 <strong>{selectedRowKeys.length}</strong> 项
          </span>
          <Space>
            <Button size="small" onClick={handleBatchEnable}>
              批量启用
            </Button>
            <Button size="small" onClick={handleBatchDisable}>
              批量禁用
            </Button>
            <Button size="small" danger onClick={handleBatchDelete}>
              批量删除
            </Button>
          </Space>
        </div>
      )}

      {/* 表格 */}
      <Card className={styles.tableCard}>
        <RuleTable
          data={filteredRules}
          loading={loading}
          selectedRowKeys={selectedRowKeys}
          onSelectionChange={setSelectedRowKeys}
          onEdit={handleEdit}
          onToggleStatus={handleToggleStatus}
          onDelete={handleDelete}
          onViewDetail={handleViewDetail}
        />
        {filteredRules.length === 0 && !loading && (
          <Empty
            description={
              hasActiveFilters ? '没有匹配的规则' : '暂无质量规则，点击上方按钮创建'
            }
            className={styles.emptyState}
          />
        )}
      </Card>
    </div>
  );
};

export default QualityRuleList;
