/**
 * 工作台 Dashboard 页面
 * 用户登录后的首页，展示核心数据概览
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  Tag,
  Button,
  Empty,
  Progress,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ProjectOutlined,
  CheckCircleOutlined,
  WalletOutlined,
  ClusterOutlined,
  ArrowRightOutlined,
  BellOutlined,
  PlusOutlined,
  NodeIndexOutlined,
  ShoppingOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  SettingOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useUserStore } from '@/store/useUserStore';
import { usePermission } from '@/hooks/usePermission';
import request from '@/services/request';
import styles from './index.module.less';

// 语义推荐相关导入
import type { RecommendedTask } from '@/types/training';
import { getRecommendedTasksSemantic } from '@/services/api/semanticMatching';
import RecommendedTaskCard from '@/components/RecommendedTaskCard';

// 统计卡片组件
interface StatCardProps {
  title: string;
  value: number | string;
  suffix?: string;
  icon: React.ReactNode;
  color: string;
  onClick?: () => void;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, suffix, icon, color, onClick }) => (
  <Card className={styles.statCard} hoverable onClick={onClick}>
    <div className={styles.statCardContent}>
      <div className={styles.statIcon} style={{ backgroundColor: color }}>
        {icon}
      </div>
      <div className={styles.statInfo}>
        <div className={styles.statTitle}>{title}</div>
        <div className={styles.statValue}>
          <Statistic value={value} suffix={suffix} valueStyle={{ fontSize: 28, fontWeight: 600 }} />
        </div>
      </div>
    </div>
  </Card>
);

// 快捷入口组件
const QuickAction: React.FC<{ icon: React.ReactNode; title: string; desc: string; onClick: () => void }> = ({
  icon,
  title,
  desc,
  onClick,
}) => (
  <Card className={styles.quickAction} hoverable onClick={onClick}>
    <div className={styles.quickActionIcon}>{icon}</div>
    <div className={styles.quickActionTitle}>{title}</div>
    <div className={styles.quickActionDesc}>{desc}</div>
  </Card>
);

// 任务状态标签
const TaskStatusTag: React.FC<{ status: string }> = ({ status }) => {
  const statusMap: Record<string, { color: string; text: string }> = {
    pending: { color: 'default', text: '待匹配' },
    matching: { color: 'processing', text: '匹配中' },
    training: { color: 'warning', text: '训练中' },
    completed: { color: 'success', text: '已完成' },
    cancelled: { color: 'error', text: '已取消' },
  };
  const { color, text } = statusMap[status] || { color: 'default', text: status };
  return <Tag color={color}>{text}</Tag>;
};

interface DashboardStats {
  pendingTasks: number;
  activeTasks: number;
  completedTasks: number;
  totalTasks: number;
}

interface RecentTask {
  id: string;
  name: string;
  status: string;
  budget: number;
  updatedAt: string;
}

interface StatusDistItem {
  name: string;
  value: number;
  color: string;
}

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useUserStore();
  const { isBuyer, isProvider, isAdmin, roleDisplayName, hasPermission } = usePermission();
  const [stats, setStats] = useState<DashboardStats>({ pendingTasks: 0, activeTasks: 0, completedTasks: 0, totalTasks: 0 });
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([]);
  const [statusDist, setStatusDist] = useState<StatusDistItem[]>([]);

  // 语义推荐任务状态
  const [recommendedTasks, setRecommendedTasks] = useState<RecommendedTask[]>([]);
  const [loadingRecommended, setLoadingRecommended] = useState(false);

  // 获取语义推荐任务
  const fetchRecommendedTasks = async () => {
    if (!isProvider) return;
    setLoadingRecommended(true);
    try {
      const res = await getRecommendedTasksSemantic(6, 0.3);
      setRecommendedTasks(res.data || []);
    } catch (error) {
      console.error('获取推荐任务失败:', error);
    } finally {
      setLoadingRecommended(false);
    }
  };

  useEffect(() => {
    // 获取任务统计
    request.get('/tasks/stats').then((res: any) => {
      const d = res.data || {};
      setStats({
        pendingTasks: d.pending || 0,
        activeTasks: d.training || 0,
        completedTasks: d.completed || 0,
        totalTasks: d.total || 0,
      });
      setStatusDist([
        { name: '待开始', value: d.pending || 0, color: '#8c8c8c' },
        { name: '训练中', value: d.training || 0, color: '#faad14' },
        { name: '已完成', value: d.completed || 0, color: '#52c41a' },
      ]);
    }).catch(() => {});

    // 获取最近任务
    request.get('/tasks').then((res: any) => {
      const tasks = (res.data || []).slice(0, 5).map((t: any) => ({
        id: t.id,
        name: t.task_name,
        status: t.status || 'pending',
        budget: t.reward_pool || 0,
        updatedAt: t.updated_at ? new Date(t.updated_at).toLocaleString() : (t.created_at ? new Date(t.created_at).toLocaleString() : '-'),
      }));
      setRecentTasks(tasks);
    }).catch(() => {});

    // 获取语义推荐任务（Provider 角色）
    fetchRecommendedTasks();
  }, []);

  // 最近任务表格列定义
  const taskColumns: ColumnsType<RecentTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: RecentTask) => (
        <a onClick={() => navigate(`/app/tasks/${record.id}`)}>{text}</a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => <TaskStatusTag status={status} />,
    },
    {
      title: '预算',
      dataIndex: 'budget',
      key: 'budget',
      width: 120,
      render: (budget: number) => `¥${budget.toLocaleString()}`,
    },
    {
      title: '更新时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: RecentTask) => (
        <Button type="link" size="small" onClick={() => navigate(`/app/tasks/${record.id}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div className={styles.dashboard}>
      {/* 欢迎语 - 角色化 */}
      <div className={styles.welcome}>
        <h1>
          欢迎回来，{user?.username || '用户'}！
          <Tag color={isAdmin ? 'red' : isProvider ? 'blue' : 'green'} style={{ marginLeft: 12, fontSize: 14, padding: '2px 10px' }}>
            {roleDisplayName}
          </Tag>
        </h1>
        <p>
          今天是 {new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })}
          {isBuyer && ' · 准备好发布新的联邦学习任务了吗？'}
          {isProvider && ' · 查看推荐任务，参与联邦学习赚取收益'}
          {isAdmin && ' · 平台管理员控制台'}
        </p>
      </div>

      {/* 统计卡片 - 角色化 */}
      <Row gutter={[24, 24]} className={styles.statRow}>
        {/* Buyer: 我的发布任务 */}
        {(isBuyer || isAdmin) && (
          <>
            <Col xs={24} sm={12} lg={6}>
              <StatCard
                title="待匹配任务"
                value={stats.pendingTasks}
                icon={<ProjectOutlined />}
                color="#722ed1"
                onClick={() => navigate('/app/my-tasks')}
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <StatCard
                title="进行中任务"
                value={stats.activeTasks}
                icon={<CheckCircleOutlined />}
                color="#1890ff"
                onClick={() => navigate('/app/my-tasks')}
              />
            </Col>
            <Col xs={24} sm={12} lg={6}>
              <StatCard
                title="已完成任务"
                value={stats.completedTasks}
                icon={<WalletOutlined />}
                color="#52c41a"
                onClick={() => navigate('/app/my-tasks')}
              />
            </Col>
          </>
        )}
        {/* Provider: 数据资产、参与任务 */}
        {(isProvider || isAdmin) && (
          <>
            <Col xs={24} sm={12} lg={isProvider ? 8 : 6}>
              <StatCard
                title="数据资产"
                value={0}
                icon={<DatabaseOutlined />}
                color="#52c41a"
                onClick={() => navigate('/app/data-assets')}
              />
            </Col>
            <Col xs={24} sm={12} lg={isProvider ? 8 : 6}>
              <StatCard
                title="参与任务"
                value={stats.activeTasks}
                icon={<CheckCircleOutlined />}
                color="#1890ff"
                onClick={() => navigate('/app/my-tasks')}
              />
            </Col>
            <Col xs={24} sm={12} lg={isProvider ? 8 : 6}>
              <StatCard
                title="累计收益"
                value={"¥0"}
                icon={<WalletOutlined />}
                color="#fa8c16"
                onClick={() => navigate('/app/profile/wallet')}
              />
            </Col>
          </>
        )}
        {/* Admin: 平台总览 */}
        {isAdmin && (
          <>
            <Col xs={24} sm={12} lg={6}>
              <StatCard
                title="平台总任务"
                value={stats.totalTasks}
                icon={<ClusterOutlined />}
                color="#ff4d4f"
                onClick={() => navigate('/app/admin/tasks')}
              />
            </Col>
          </>
        )}
      </Row>

      {/* 快捷入口 - 角色化 */}
      <Card title="快捷入口" className={styles.sectionCard}>
        <Row gutter={[16, 16]}>
          {/* Buyer: 发布任务 */}
          {hasPermission('task:publish') && (
            <Col xs={12} sm={6}>
              <QuickAction
                icon={<PlusOutlined style={{ color: '#1890ff' }} />}
                title="发布任务"
                desc="创建新的联邦学习任务"
                onClick={() => navigate('/app/tasks/publish')}
              />
            </Col>
          )}
          {/* Provider: 数据资产 */}
          {hasPermission('dataasset:view') && (
            <Col xs={12} sm={6}>
              <QuickAction
                icon={<DatabaseOutlined style={{ color: '#52c41a' }} />}
                title="数据资产"
                desc="管理您的数据资产"
                onClick={() => navigate('/app/data-assets')}
              />
            </Col>
          )}
          {/* Provider: 推荐任务 */}
          {hasPermission('task:join') && (
            <Col xs={12} sm={6}>
              <QuickAction
                icon={<FileSearchOutlined style={{ color: '#722ed1' }} />}
                title="推荐任务"
                desc="发现适合参与的任务"
                onClick={() => navigate('/app/matching')}
              />
            </Col>
          )}
          {/* All: 节点管理 */}
          <Col xs={12} sm={6}>
            <QuickAction
              icon={<NodeIndexOutlined style={{ color: '#13c2c2' }} />}
              title="边缘节点"
              desc="查看和管理边缘节点"
              onClick={() => navigate('/app/edge-nodes')}
            />
          </Col>
          {/* All: 浏览市场 */}
          <Col xs={12} sm={6}>
            <QuickAction
              icon={<ShoppingOutlined style={{ color: '#eb2f96' }} />}
              title="任务大厅"
              desc="浏览数据任务市场"
              onClick={() => navigate('/app/tasks')}
            />
          </Col>
          {/* All: 钱包 */}
          <Col xs={12} sm={6}>
            <QuickAction
              icon={<WalletOutlined style={{ color: '#fa8c16' }} />}
              title="查看收益"
              desc="查看钱包和交易记录"
              onClick={() => navigate('/app/profile/wallet')}
            />
          </Col>
          {/* Admin: 管理后台 */}
          {isAdmin && (
            <Col xs={12} sm={6}>
              <QuickAction
                icon={<SettingOutlined style={{ color: '#ff4d4f' }} />}
                title="管理后台"
                desc="平台全局管理"
                onClick={() => navigate('/app/admin')}
              />
            </Col>
          )}
        </Row>
      </Card>

      {/* 图表区域 */}
      <Row gutter={[24, 24]} className={styles.chartRow}>
        <Col xs={24} lg={8}>
          <Card
            title="任务状态分布"
            className={styles.chartCard}
          >
            <div className={styles.statusDistribution}>
              {statusDist.map((item) => (
                <div key={item.name} className={styles.statusItem}>
                  <div className={styles.statusHeader}>
                    <span className={styles.statusDot} style={{ backgroundColor: item.color }} />
                    <span className={styles.statusName}>{item.name}</span>
                    <span className={styles.statusValue}>{item.value}</span>
                  </div>
                  <Progress
                    percent={stats.totalTasks > 0 ? Math.round((item.value / stats.totalTasks) * 100) : 0}
                    strokeColor={item.color}
                    showInfo={false}
                  />
                </div>
              ))}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Provider 专属：语义推荐任务 */}
      {isProvider && (
        <Card
          title={
            <span>
              <FileSearchOutlined style={{ marginRight: 8, color: '#722ed1' }} />
              为您推荐的任务
            </span>
          }
          className={styles.sectionCard}
          style={{ marginBottom: 24 }}
          extra={
            <Button
              type="link"
              icon={<ReloadOutlined spin={loadingRecommended} />}
              onClick={fetchRecommendedTasks}
              disabled={loadingRecommended}
            >
              刷新推荐
            </Button>
          }
        >
          {loadingRecommended ? (
            <Row gutter={[16, 16]}>
              {[1, 2, 3].map((i) => (
                <Col xs={24} md={12} xl={8} key={i}>
                  <Card loading bodyStyle={{ padding: '16px' }} />
                </Col>
              ))}
            </Row>
          ) : recommendedTasks.length > 0 ? (
            <Row gutter={[16, 16]}>
              {recommendedTasks.map((task) => (
                <Col xs={24} md={12} xl={8} key={task.task_id}>
                  <RecommendedTaskCard
                    task={task}
                    onViewDetail={(id) => navigate(`/app/tasks/${id}`)}
                    onJoin={(id) => navigate(`/app/tasks/${id}/join`)}
                  />
                </Col>
              ))}
            </Row>
          ) : (
            <Empty
              description={
                <span>
                  暂无推荐任务
                  <br />
                  <small style={{ color: '#999' }}>完善您的数据资产信息以获得更精准的推荐</small>
                </span>
              }
            >
              <Button type="primary" onClick={() => navigate('/app/data-assets')}>
                去完善数据资产
              </Button>
            </Empty>
          )}
        </Card>
      )}

      {/* 下方内容区 */}
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card
            title={isProvider ? '推荐任务' : '最近任务'}
            className={styles.sectionCard}
            extra={
              <Button type="link" onClick={() => navigate(isProvider ? '/matching' : '/my-tasks')}>
                查看全部 <ArrowRightOutlined />
              </Button>
            }
          >
            <Table
              columns={taskColumns}
              dataSource={recentTasks}
              rowKey="id"
              pagination={false}
              size="small"
              locale={{
                emptyText: (
                  <Empty
                    description={
                      isProvider
                        ? '暂无推荐任务，请完善数据资产信息'
                        : isBuyer
                          ? '暂无任务，去发布第一个任务吧'
                          : '暂无任务数据'
                    }
                  />
                ),
              }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            title={
              <span>
                <BellOutlined style={{ marginRight: 8 }} />
                系统通知
              </span>
            }
            className={styles.sectionCard}
          >
            <Empty description="暂无通知" />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
