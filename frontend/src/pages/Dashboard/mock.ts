/**
 * Dashboard 页面 Mock 数据
 */

// 仪表盘统计数据
export const mockDashboardData = {
  pendingTasks: 3,
  activeTasks: 5,
  completedTasks: 12,
  monthlyRevenue: 25800,
  totalRevenue: 156000,
  onlineNodes: 8,
  totalNodes: 10,
};

// 最近任务列表
export const mockRecentTasks = [
  {
    id: 'TASK-001',
    name: '医疗影像分类模型训练',
    status: 'training',
    budget: 50000,
    updatedAt: '2024-01-20 14:30',
    type: '联邦学习',
  },
  {
    id: 'TASK-002',
    name: '金融风控预测模型',
    status: 'completed',
    budget: 100000,
    updatedAt: '2024-01-18 16:00',
    type: '联邦学习',
  },
  {
    id: 'TASK-003',
    name: '智能推荐系统模型',
    status: 'pending',
    budget: 80000,
    updatedAt: '2024-01-19 11:00',
    type: '联邦学习',
  },
  {
    id: 'TASK-004',
    name: '语音识别增强模型',
    status: 'matching',
    budget: 120000,
    updatedAt: '2024-01-20 14:00',
    type: '联邦学习',
  },
  {
    id: 'TASK-005',
    name: '异常检测模型',
    status: 'cancelled',
    budget: 30000,
    updatedAt: '2024-01-14 09:00',
    type: '联邦学习',
  },
];

// 系统通知
export const mockNotifications = [
  {
    id: '1',
    title: '您参与的任务 "医疗影像分类模型训练" 已完成第 67 轮训练',
    time: '10 分钟前',
    read: false,
  },
  {
    id: '2',
    title: '节点 "北京数据中心-节点01" 已恢复在线状态',
    time: '1 小时前',
    read: false,
  },
  {
    id: '3',
    title: '您发布的任务 "金融风控预测模型" 已结算完成',
    time: '2 小时前',
    read: true,
  },
  {
    id: '4',
    title: '系统维护通知：本周日凌晨 2:00-4:00 进行例行维护',
    time: '1 天前',
    read: true,
  },
  {
    id: '5',
    title: '恭喜！您已获得 "优质数据提供方" 认证标识',
    time: '2 天前',
    read: true,
  },
];

// 一周趋势数据
export const mockWeeklyTrend = [
  { name: '周一', tasks: 4, revenue: 1200, nodes: 8 },
  { name: '周二', tasks: 3, revenue: 800, nodes: 8 },
  { name: '周三', tasks: 5, revenue: 1500, nodes: 9 },
  { name: '周四', tasks: 2, revenue: 600, nodes: 8 },
  { name: '周五', tasks: 6, revenue: 2000, nodes: 10 },
  { name: '周六', tasks: 4, revenue: 1300, nodes: 9 },
  { name: '周日', tasks: 3, revenue: 900, nodes: 8 },
];

// 任务状态分布
export const mockTaskStatusDistribution = [
  { name: '待匹配', value: 3, color: '#8c8c8c' },
  { name: '匹配中', value: 2, color: '#1890ff' },
  { name: '训练中', value: 5, color: '#faad14' },
  { name: '已完成', value: 12, color: '#52c41a' },
];
