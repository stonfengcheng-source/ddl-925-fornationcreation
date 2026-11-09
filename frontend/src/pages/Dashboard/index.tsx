/**
 * 登录后的工作台。
 *
 * 页面只保留用户最常用的三类信息：现在的状态、下一步入口、最近的任务。
 * 不把每一个数字和功能都拆成独立小卡片，避免造成“信息很多但不知道先做什么”的感觉。
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Button,
  Card,
  Empty,
  Progress,
  Table,
  Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import {
  ArrowRightOutlined,
  BellOutlined,
  CheckCircleOutlined,
  ClusterOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  NodeIndexOutlined,
  PlusOutlined,
  ProjectOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  ShoppingOutlined,
  TeamOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import { useUserStore } from '@/store/useUserStore';
import { usePermission } from '@/hooks/usePermission';
import request from '@/services/request';
import type { RecommendedTask } from '@/types/training';
import { getRecommendedTasksSemantic } from '@/services/api/semanticMatching';
import styles from './index.module.less';
import ProductStart from './ProductStart';

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

interface MetricItem {
  label: string;
  value: number | string;
  hint: string;
  icon: React.ReactNode;
  tone: 'blue' | 'purple' | 'orange' | 'green';
  onClick: () => void;
}

interface WorkflowItem {
  label: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  tone: 'blue' | 'green' | 'purple';
  href: string;
}

const statusMap: Record<string, { color: string; text: string }> = {
  pending: { color: 'default', text: '待匹配' },
  matching: { color: 'processing', text: '匹配中' },
  training: { color: 'warning', text: '训练中' },
  running: { color: 'warning', text: '训练中' },
  completed: { color: 'success', text: '已完成' },
  settled: { color: 'success', text: '已结算' },
  cancelled: { color: 'error', text: '已取消' },
  failed: { color: 'error', text: '失败' },
};

const TaskStatusTag: React.FC<{ status: string }> = ({ status }) => {
  const config = statusMap[status] || { color: 'default', text: status || '未知' };
  return <Tag color={config.color}>{config.text}</Tag>;
};

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useUserStore();
  const { isProvider, isAdmin, roleDisplayName, hasPermission } = usePermission();
  const [stats, setStats] = useState<DashboardStats>({ pendingTasks: 0, activeTasks: 0, completedTasks: 0, totalTasks: 0 });
  const [recentTasks, setRecentTasks] = useState<RecentTask[]>([]);
  const [recommendedTasks, setRecommendedTasks] = useState<RecommendedTask[]>([]);
  const [loadingRecommended, setLoadingRecommended] = useState(false);
  const [statusDist, setStatusDist] = useState<StatusDistItem[]>([
    { name: '待开始', value: 0, color: '#98a2b3' },
    { name: '训练中', value: 0, color: '#f59e0b' },
    { name: '已完成', value: 0, color: '#16a37a' },
  ]);

  const fetchRecommendedTasks = useCallback(async () => {
    if (!isProvider) return;
    setLoadingRecommended(true);
    try {
      const response = await getRecommendedTasksSemantic(6, 0.3);
      setRecommendedTasks(response.data || []);
    } catch {
      setRecommendedTasks([]);
    } finally {
      setLoadingRecommended(false);
    }
  }, [isProvider]);

  useEffect(() => {
    request.get('/tasks/stats').then((response: any) => {
      const data = response?.data || {};
      setStats({
        pendingTasks: data.pending || 0,
        activeTasks: data.training || 0,
        completedTasks: data.completed || 0,
        totalTasks: data.total || 0,
      });
      setStatusDist([
        { name: '待开始', value: data.pending || 0, color: '#98a2b3' },
        { name: '训练中', value: data.training || 0, color: '#f59e0b' },
        { name: '已完成', value: data.completed || 0, color: '#16a37a' },
      ]);
    }).catch(() => undefined);

    request.get('/tasks').then((response: any) => {
      const list = Array.isArray(response?.data) ? response.data : [];
      setRecentTasks(list.slice(0, 5).map((task: any) => ({
        id: task.id,
        name: task.task_name || '未命名任务',
        status: task.status || 'pending',
        budget: task.reward_pool || 0,
        updatedAt: task.updated_at
          ? new Date(task.updated_at).toLocaleString()
          : task.created_at
            ? new Date(task.created_at).toLocaleString()
            : '-',
      })));
    }).catch(() => setRecentTasks([]));

    void fetchRecommendedTasks();
  }, [fetchRecommendedTasks]);

  const metrics = useMemo<MetricItem[]>(() => {
    if (isAdmin) {
      return [
        { label: '平台任务', value: stats.totalTasks, hint: '全部任务规模', icon: <ProjectOutlined />, tone: 'blue', onClick: () => navigate('/app/admin/tasks') },
        { label: '待匹配', value: stats.pendingTasks, hint: '等待数据节点加入', icon: <ClusterOutlined />, tone: 'purple', onClick: () => navigate('/app/my-tasks') },
        { label: '训练中', value: stats.activeTasks, hint: '可进入训练监控', icon: <SafetyCertificateOutlined />, tone: 'orange', onClick: () => navigate('/app/my-tasks') },
        { label: '已完成', value: stats.completedTasks, hint: '已完成的协作任务', icon: <CheckCircleOutlined />, tone: 'green', onClick: () => navigate('/app/my-tasks') },
      ];
    }
    if (isProvider) {
      return [
        { label: '参与任务', value: stats.activeTasks, hint: '正在参与的联合训练', icon: <TeamOutlined />, tone: 'blue', onClick: () => navigate('/app/my-tasks') },
        { label: '推荐任务', value: recommendedTasks.length, hint: '根据数据资产匹配', icon: <FileSearchOutlined />, tone: 'purple', onClick: () => navigate('/app/matching') },
        { label: '数据资产', value: 0, hint: '登记后即可参与匹配', icon: <DatabaseOutlined />, tone: 'green', onClick: () => navigate('/app/data-assets') },
        { label: '累计收益', value: '¥0', hint: '训练完成后查看结算', icon: <WalletOutlined />, tone: 'orange', onClick: () => navigate('/app/profile/wallet') },
      ];
    }
    return [
      { label: '全部任务', value: stats.totalTasks, hint: '我发起的协作任务', icon: <ProjectOutlined />, tone: 'blue', onClick: () => navigate('/app/my-tasks') },
      { label: '待匹配', value: stats.pendingTasks, hint: '等待数据节点加入', icon: <ClusterOutlined />, tone: 'purple', onClick: () => navigate('/app/my-tasks') },
      { label: '训练中', value: stats.activeTasks, hint: '可进入训练监控', icon: <SafetyCertificateOutlined />, tone: 'orange', onClick: () => navigate('/app/my-tasks') },
      { label: '已完成', value: stats.completedTasks, hint: '可查看任务结果', icon: <CheckCircleOutlined />, tone: 'green', onClick: () => navigate('/app/my-tasks') },
    ];
  }, [isAdmin, isProvider, navigate, recommendedTasks.length, stats]);

  const workflow = useMemo<WorkflowItem[]>(() => {
    if (isProvider && !isAdmin) {
      return [
        { label: '01', title: '完善数据资产', description: '先登记数据的类型、规模和质量，系统才能找到适合你的任务。', icon: <DatabaseOutlined />, tone: 'green', href: '/app/data-assets' },
        { label: '02', title: '查看推荐任务', description: '查看与你的数据最匹配的协作机会，再决定是否参与。', icon: <FileSearchOutlined />, tone: 'purple', href: '/app/matching' },
        { label: '03', title: '进入训练监控', description: '节点就绪后查看训练进度，原始数据始终保留在本地。', icon: <NodeIndexOutlined />, tone: 'blue', href: '/app/my-tasks' },
      ];
    }
    return [
      hasPermission('task:publish')
        ? { label: '01', title: '发布协作任务', description: '设置训练目标、参与条件和奖励池，提出清晰的数据需求。', icon: <PlusOutlined />, tone: 'blue' as const, href: '/app/tasks/publish' }
        : { label: '01', title: '浏览任务大厅', description: '先了解当前平台有哪些公开的联邦学习协作机会。', icon: <ShoppingOutlined />, tone: 'blue' as const, href: '/app/tasks' },
      { label: '02', title: '管理我的任务', description: '集中查看任务状态；训练开始后，从这里进入训练监控。', icon: <ProjectOutlined />, tone: 'purple', href: '/app/my-tasks' },
      isAdmin
        ? { label: '03', title: '查看平台管理', description: '管理平台用户和任务，了解整体运行情况。', icon: <SettingOutlined />, tone: 'green' as const, href: '/app/admin' }
        : { label: '03', title: '检查隐私预算', description: '查看训练中的隐私消耗，确保协作过程可控、可解释。', icon: <SafetyCertificateOutlined />, tone: 'green' as const, href: '/app/privacy-budget' },
    ];
  }, [hasPermission, isAdmin, isProvider]);

  const taskColumns: ColumnsType<RecentTask> = [
    {
      title: '任务名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name: string, record: RecentTask) => <button type="button" className={styles.taskName} onClick={() => navigate(`/app/tasks/${record.id}`)}>{name}</button>,
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (status: string) => <TaskStatusTag status={status} /> },
    { title: '奖励池', dataIndex: 'budget', key: 'budget', width: 120, render: (budget: number) => `¥${budget.toLocaleString()}` },
    { title: '最近更新', dataIndex: 'updatedAt', key: 'updatedAt', width: 170 },
    { title: '操作', key: 'action', width: 80, render: (_: unknown, record: RecentTask) => <Button type="link" size="small" onClick={() => navigate(`/app/tasks/${record.id}`)}>查看</Button> },
  ];

  const greeting = isProvider ? '从数据资产开始，找到适合你的协作机会。' : isAdmin ? '这里可以快速查看平台运行状态和待处理事项。' : '从发布一个清晰的协作任务开始。';

  return (
    <div className={styles.dashboard}>
      {!isProvider && <ProductStart />}
      {isProvider && <>
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <Tag color="blue" className={styles.heroTag} icon={<SafetyCertificateOutlined />}>联邦协作工作台</Tag>
          <h1>欢迎回来，<em>{user?.username || '用户'}</em></h1>
          <p className={styles.heroSubtitle}>{greeting}</p>
          <p className={styles.heroDescription}>数据留在本地，模型通过安全协作共同训练。你可以从下方的主流程开始，不需要一次理解全部模块。</p>
          <div className={styles.heroActions}>
            {hasPermission('task:publish') && <Button type="primary" size="large" icon={<PlusOutlined />} onClick={() => navigate('/app/tasks/publish')}>发布任务</Button>}
            <Button size="large" onClick={() => navigate('/app/tasks')}>查看任务大厅 <ArrowRightOutlined /></Button>
          </div>
          <div className={styles.heroMeta}><span><CheckCircleOutlined /> 当前身份：{roleDisplayName}</span><span><SafetyCertificateOutlined /> 本地开发免密模式</span></div>
        </div>
        <div className={styles.heroVisual} aria-label="联邦协作流程示意">
          <div className={styles.flowCard}>
            <div className={styles.flowHeader}><div><strong>一次协作如何完成</strong><span>原始数据不出域</span></div><span className={styles.liveDot}>安全运行</span></div>
            <div className={styles.flowNodes}>
              <FlowNode icon={<DatabaseOutlined />} label="数据资产" tone="green" />
              <FlowNode icon={<NodeIndexOutlined />} label="训练节点" tone="blue" />
              <FlowNode icon={<ClusterOutlined />} label="任务协作" tone="orange" />
            </div>
            <div className={styles.flowArrow}>↓　↓　↓</div>
            <div className={styles.flowCenter}><strong>联邦聚合中心</strong><span>只交换模型参数</span></div>
            <div className={styles.flowArrow}>↑</div>
            <div className={styles.flowResult}><CheckCircleOutlined /><span><strong>联合模型</strong>　可审计、可复用</span></div>
          </div>
        </div>
      </section>

      <section className={styles.overviewPanel}>
        <div className={styles.overviewIntro}><span className={styles.eyebrow}>OVERVIEW</span><h2>先看全局，再开始操作</h2><p>这些数字只用于帮助你判断当前阶段，不需要逐项处理。</p></div>
        <div className={styles.overviewMetrics}>{metrics.map((metric) => <OverviewMetric key={metric.label} {...metric} />)}</div>
      </section>

      <section className={styles.workflowSection}>
        <div className={styles.sectionHeading}><div><span className={styles.eyebrow}>YOUR NEXT STEP</span><h2>接下来做什么？</h2><p>按顺序完成即可，不需要同时打开多个模块。</p></div><Tag color="blue">{isProvider ? '数据提供方路径' : isAdmin ? '管理员路径' : '需求方路径'}</Tag></div>
        <div className={styles.workflowGrid}>{workflow.map((item) => <WorkflowCard key={item.label} item={item} onClick={() => navigate(item.href)} />)}</div>
      </section>

      <section className={styles.taskSection}>
        <Card title={<div className={styles.cardTitle}><ProjectOutlined /><span>最近任务</span><small>从这里进入详情或训练监控</small></div>} className={styles.sectionCard} extra={<Button type="link" onClick={() => navigate('/app/my-tasks')}>查看全部 <ArrowRightOutlined /></Button>}>
          <Table columns={taskColumns} dataSource={recentTasks} rowKey="id" pagination={false} scroll={{ x: 600 }} locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有任务，先完成上面的第一步吧" /> }} />
        </Card>
        <div className={styles.progressPanel}>
          <div className={styles.panelHeader}><div><span className={styles.eyebrow}>STATUS</span><h3>当前进度</h3></div><BellOutlined /></div>
          <p className={styles.panelIntro}>用这条进度带判断平台当前处于哪个阶段。</p>
          <div className={styles.statusDistribution}>{statusDist.map((item) => <div key={item.name} className={styles.statusItem}><div className={styles.statusHeader}><span className={styles.statusDot} style={{ backgroundColor: item.color }} /><span className={styles.statusName}>{item.name}</span><span className={styles.statusValue}>{item.value}</span></div><Progress percent={stats.totalTasks > 0 ? Math.round((item.value / stats.totalTasks) * 100) : 0} strokeColor={item.color} showInfo={false} /></div>)}</div>
          <div className={styles.nextStep}><SafetyCertificateOutlined /><div><strong>训练监控是当前主流程</strong><p>节点就绪后，从“我的任务”进入训练监控，启动并查看训练进度。</p></div></div>
        </div>
      </section>

      <section className={styles.recommendSection}><div className={styles.sectionHeading}><div><span className={styles.eyebrow}>RECOMMENDED</span><h2>为你推荐的任务</h2><p>基于已登记的数据资产匹配，先浏览再决定是否参与。</p></div><Button type="link" icon={<ReloadOutlined spin={loadingRecommended} />} onClick={fetchRecommendedTasks} disabled={loadingRecommended}>刷新推荐</Button></div>{loadingRecommended ? <div className={styles.recommendEmpty}>正在分析适合你的任务...</div> : recommendedTasks.length ? <div className={styles.recommendGrid}>{recommendedTasks.slice(0, 3).map((task) => <button type="button" className={styles.recommendItem} key={task.task_id} onClick={() => navigate(`/app/tasks/${task.task_id}`)}><div><strong>{task.task_name || '推荐任务'}</strong><p>{task.description || task.category || '与你的数据资产匹配度较高'}</p></div><ArrowRightOutlined /></button>)}</div> : <div className={styles.recommendEmpty}><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂时没有推荐任务，先完善数据资产信息" /></div>}</section>
      </>}
    </div>
  );
};

const OverviewMetric: React.FC<MetricItem> = ({ label, value, hint, icon, tone, onClick }) => <button type="button" className={`${styles.overviewMetric} ${styles[`metric${tone}`]}`} onClick={onClick}><span className={styles.metricIcon}>{icon}</span><span className={styles.metricCopy}><span className={styles.metricLabel}>{label}</span><strong>{value}</strong><small>{hint}</small></span><ArrowRightOutlined className={styles.metricArrow} /></button>;

const WorkflowCard: React.FC<{ item: WorkflowItem; onClick: () => void }> = ({ item, onClick }) => <button type="button" className={`${styles.workflowCard} ${styles[`workflow${item.tone}`]}`} onClick={onClick}><span className={styles.workflowNumber}>{item.label}</span><span className={styles.workflowIcon}>{item.icon}</span><span className={styles.workflowTitle}>{item.title}</span><span className={styles.workflowDescription}>{item.description}</span><span className={styles.workflowLink}>开始 <ArrowRightOutlined /></span></button>;

const FlowNode: React.FC<{ icon: React.ReactNode; label: string; tone: 'green' | 'blue' | 'orange' }> = ({ icon, label, tone }) => <div className={`${styles.flowNode} ${styles[`flowNode${tone}`]}`}><span>{icon}</span><b>{label}</b></div>;

export default Dashboard;
