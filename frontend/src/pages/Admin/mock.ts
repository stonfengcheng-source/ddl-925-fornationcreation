/**
 * Admin 管理后台 Mock 数据
 */

// 仪表盘统计数据
export const mockAdminDashboardData = {
  // 核心指标
  totalUsers: 12580,
  totalTasks: 3420,
  totalNodes: 156,
  totalRevenue: 2580000,

  // 今日数据
  todayNewUsers: 45,
  todayNewTasks: 12,
  todayRevenue: 12800,

  // 用户增长趋势（近30天）
  userGrowthTrend: [
    { date: '01-01', newUsers: 32, activeUsers: 1200 },
    { date: '01-02', newUsers: 28, activeUsers: 1150 },
    { date: '01-03', newUsers: 45, activeUsers: 1300 },
    { date: '01-04', newUsers: 38, activeUsers: 1250 },
    { date: '01-05', newUsers: 52, activeUsers: 1400 },
    { date: '01-06', newUsers: 41, activeUsers: 1350 },
    { date: '01-07', newUsers: 35, activeUsers: 1280 },
    { date: '01-08', newUsers: 48, activeUsers: 1420 },
    { date: '01-09', newUsers: 55, activeUsers: 1500 },
    { date: '01-10', newUsers: 42, activeUsers: 1450 },
    { date: '01-11', newUsers: 38, activeUsers: 1380 },
    { date: '01-12', newUsers: 50, activeUsers: 1520 },
    { date: '01-13', newUsers: 46, activeUsers: 1480 },
    { date: '01-14', newUsers: 33, activeUsers: 1320 },
    { date: '01-15', newUsers: 40, activeUsers: 1400 },
    { date: '01-16', newUsers: 58, activeUsers: 1600 },
    { date: '01-17', newUsers: 62, activeUsers: 1650 },
    { date: '01-18', newUsers: 49, activeUsers: 1550 },
    { date: '01-19', newUsers: 44, activeUsers: 1500 },
    { date: '01-20', newUsers: 51, activeUsers: 1580 },
    { date: '01-21', newUsers: 47, activeUsers: 1520 },
    { date: '01-22', newUsers: 39, activeUsers: 1450 },
    { date: '01-23', newUsers: 43, activeUsers: 1480 },
    { date: '01-24', newUsers: 56, activeUsers: 1620 },
    { date: '01-25', newUsers: 61, activeUsers: 1680 },
    { date: '01-26', newUsers: 53, activeUsers: 1590 },
    { date: '01-27', newUsers: 48, activeUsers: 1540 },
    { date: '01-28', newUsers: 42, activeUsers: 1490 },
    { date: '01-29', newUsers: 50, activeUsers: 1560 },
    { date: '01-30', newUsers: 45, activeUsers: 1520 },
  ],

  // 任务分布
  taskDistribution: [
    { name: '医疗影像', value: 850, color: '#1890ff' },
    { name: '金融风控', value: 620, color: '#52c41a' },
    { name: '智能推荐', value: 480, color: '#722ed1' },
    { name: '语音识别', value: 320, color: '#fa8c16' },
    { name: '自然语言', value: 280, color: '#eb2f96' },
    { name: '其他', value: 870, color: '#8c8c8c' },
  ],

  // 任务状态分布
  taskStatusDistribution: [
    { name: '待审核', value: 45, color: '#faad14' },
    { name: '进行中', value: 680, color: '#1890ff' },
    { name: '已完成', value: 2450, color: '#52c41a' },
    { name: '已取消', value: 245, color: '#8c8c8c' },
  ],

  // 节点状态分布
  nodeStatusDistribution: [
    { name: '在线', value: 128, color: '#52c41a' },
    { name: '离线', value: 18, color: '#8c8c8c' },
    { name: '维护中', value: 10, color: '#faad14' },
  ],

  // 收入趋势（近12个月）
  revenueTrend: [
    { month: '2023-02', revenue: 180000, expense: 120000 },
    { month: '2023-03', revenue: 220000, expense: 145000 },
    { month: '2023-04', revenue: 195000, expense: 130000 },
    { month: '2023-05', revenue: 280000, expense: 180000 },
    { month: '2023-06', revenue: 320000, expense: 210000 },
    { month: '2023-07', revenue: 290000, expense: 195000 },
    { month: '2023-08', revenue: 350000, expense: 230000 },
    { month: '2023-09', revenue: 380000, expense: 250000 },
    { month: '2023-10', revenue: 420000, expense: 280000 },
    { month: '2023-11', revenue: 390000, expense: 260000 },
    { month: '2023-12', revenue: 450000, expense: 300000 },
    { month: '2024-01', revenue: 258000, expense: 172000 },
  ],
};

// 最近交易流水
export const mockRecentTransactions = [
  { id: 'TXN-20240120001', type: 'task_payment', amount: 50000, user: '张三', status: 'completed', time: '2024-01-20 14:30:25' },
  { id: 'TXN-20240120002', type: 'node_reward', amount: 2500, user: '李四', status: 'completed', time: '2024-01-20 13:15:10' },
  { id: 'TXN-20240120003', type: 'withdrawal', amount: -10000, user: '王五', status: 'pending', time: '2024-01-20 12:45:33' },
  { id: 'TXN-20240120004', type: 'task_payment', amount: 80000, user: '赵六', status: 'completed', time: '2024-01-20 11:20:15' },
  { id: 'TXN-20240120005', type: 'node_reward', amount: 1800, user: '钱七', status: 'completed', time: '2024-01-20 10:05:42' },
  { id: 'TXN-20240119006', type: 'task_payment', amount: 120000, user: '孙八', status: 'completed', time: '2024-01-19 16:30:00' },
  { id: 'TXN-20240119007', type: 'withdrawal', amount: -5000, user: '周九', status: 'completed', time: '2024-01-19 15:20:18' },
  { id: 'TXN-20240119008', type: 'node_reward', amount: 3200, user: '吴十', status: 'completed', time: '2024-01-19 14:10:05' },
];

// 系统告警
export const mockSystemAlerts = [
  { id: '1', level: 'warning', title: '节点 Node-Beijing-03 离线超过30分钟', time: '10分钟前', resolved: false },
  { id: '2', level: 'error', title: '任务 TASK-2024-0156 训练异常中断', time: '25分钟前', resolved: false },
  { id: '3', level: 'info', title: '系统备份完成', time: '1小时前', resolved: true },
  { id: '4', level: 'warning', title: '存储空间使用率超过80%', time: '2小时前', resolved: false },
  { id: '5', level: 'info', title: '新版本 v2.1.0 发布', time: '3小时前', resolved: true },
];

// 用户列表
export const mockUserList = [
  { id: 'USR-001', username: '张三', email: 'zhangsan@example.com', role: 'enterprise', status: 'active', createdAt: '2023-06-15', lastLogin: '2024-01-20 14:30', taskCount: 45, balance: 125000 },
  { id: 'USR-002', username: '李四', email: 'lisi@example.com', role: 'provider', status: 'active', createdAt: '2023-07-20', lastLogin: '2024-01-20 13:15', taskCount: 0, balance: 25800 },
  { id: 'USR-003', username: '王五', email: 'wangwu@example.com', role: 'enterprise', status: 'inactive', createdAt: '2023-08-10', lastLogin: '2024-01-15 09:20', taskCount: 12, balance: 50000 },
  { id: 'USR-004', username: '赵六', email: 'zhaoliu@example.com', role: 'admin', status: 'active', createdAt: '2023-01-01', lastLogin: '2024-01-20 16:00', taskCount: 0, balance: 0 },
  { id: 'USR-005', username: '钱七', email: 'qianqi@example.com', role: 'provider', status: 'active', createdAt: '2023-09-05', lastLogin: '2024-01-20 10:05', taskCount: 0, balance: 15600 },
  { id: 'USR-006', username: '孙八', email: 'sunba@example.com', role: 'enterprise', status: 'active', createdAt: '2023-10-12', lastLogin: '2024-01-19 18:30', taskCount: 28, balance: 89000 },
  { id: 'USR-007', username: '周九', email: 'zhoujiu@example.com', role: 'provider', status: 'suspended', createdAt: '2023-11-20', lastLogin: '2024-01-10 11:20', taskCount: 0, balance: 3200 },
  { id: 'USR-008', username: '吴十', email: 'wushi@example.com', role: 'provider', status: 'active', createdAt: '2023-12-01', lastLogin: '2024-01-20 09:45', taskCount: 0, balance: 41200 },
];

// 任务列表
export const mockTaskList = [
  { id: 'TASK-001', name: '医疗影像分类模型训练', publisher: '张三', type: '联邦学习', budget: 50000, status: 'training', progress: 67, createdAt: '2024-01-15', deadline: '2024-02-15' },
  { id: 'TASK-002', name: '金融风控预测模型', publisher: '孙八', type: '联邦学习', budget: 100000, status: 'completed', progress: 100, createdAt: '2024-01-10', deadline: '2024-02-10' },
  { id: 'TASK-003', name: '智能推荐系统模型', publisher: '王五', type: '联邦学习', budget: 80000, status: 'pending', progress: 0, createdAt: '2024-01-20', deadline: '2024-02-20' },
  { id: 'TASK-004', name: '语音识别增强模型', publisher: '张三', type: '联邦学习', budget: 120000, status: 'matching', progress: 25, createdAt: '2024-01-18', deadline: '2024-02-28' },
  { id: 'TASK-005', name: '异常检测模型', publisher: '孙八', type: '联邦学习', budget: 30000, status: 'cancelled', progress: 0, createdAt: '2024-01-12', deadline: '2024-02-12' },
  { id: 'TASK-006', name: '自然语言处理模型', publisher: '张三', type: '联邦学习', budget: 150000, status: 'training', progress: 45, createdAt: '2024-01-16', deadline: '2024-03-01' },
  { id: 'TASK-007', name: '图像识别模型', publisher: '王五', type: '联邦学习', budget: 60000, status: 'pending', progress: 0, createdAt: '2024-01-19', deadline: '2024-02-19' },
  { id: 'TASK-008', name: '时序预测模型', publisher: '孙八', type: '联邦学习', budget: 75000, status: 'matching', progress: 10, createdAt: '2024-01-17', deadline: '2024-02-25' },
];

// 节点列表
export const mockNodeList = [
  { id: 'NODE-BJ-001', name: '北京数据中心-节点01', location: '北京', owner: '李四', status: 'online', health: 98, cpu: 45, memory: 62, storage: 78, lastHeartbeat: '2024-01-20 14:30:25', tasks: 12 },
  { id: 'NODE-BJ-002', name: '北京数据中心-节点02', location: '北京', owner: '钱七', status: 'online', health: 95, cpu: 38, memory: 55, storage: 65, lastHeartbeat: '2024-01-20 14:29:18', tasks: 8 },
  { id: 'NODE-SH-001', name: '上海云节点-01', location: '上海', owner: '吴十', status: 'online', health: 92, cpu: 52, memory: 68, storage: 72, lastHeartbeat: '2024-01-20 14:28:45', tasks: 15 },
  { id: 'NODE-SH-002', name: '上海云节点-02', location: '上海', owner: '李四', status: 'offline', health: 0, cpu: 0, memory: 0, storage: 0, lastHeartbeat: '2024-01-20 13:50:00', tasks: 0 },
  { id: 'NODE-GZ-001', name: '广州边缘节点-01', location: '广州', owner: '钱七', status: 'maintenance', health: 75, cpu: 0, memory: 0, storage: 85, lastHeartbeat: '2024-01-20 14:25:30', tasks: 0 },
  { id: 'NODE-SZ-001', name: '深圳智算节点-01', location: '深圳', owner: '吴十', status: 'online', health: 96, cpu: 41, memory: 58, storage: 70, lastHeartbeat: '2024-01-20 14:30:10', tasks: 10 },
  { id: 'NODE-HZ-001', name: '杭州云节点-01', location: '杭州', owner: '李四', status: 'online', health: 94, cpu: 35, memory: 48, storage: 60, lastHeartbeat: '2024-01-20 14:29:55', tasks: 6 },
  { id: 'NODE-CD-001', name: '成都边缘节点-01', location: '成都', owner: '钱七', status: 'online', health: 90, cpu: 48, memory: 65, storage: 75, lastHeartbeat: '2024-01-20 14:28:20', tasks: 9 },
];

// 待审批节点
export const mockPendingNodes = [
  { id: 'NODE-REQ-001', name: '武汉智算中心-节点01', location: '武汉', owner: '郑十一', applyTime: '2024-01-20 10:30:00', specs: { cpu: '32核', memory: '128GB', storage: '2TB', gpu: 'NVIDIA A100 x 4' } },
  { id: 'NODE-REQ-002', name: '西安数据中心-节点01', location: '西安', owner: '王十二', applyTime: '2024-01-20 09:15:00', specs: { cpu: '64核', memory: '256GB', storage: '4TB', gpu: 'NVIDIA V100 x 8' } },
  { id: 'NODE-REQ-003', name: '南京云节点-01', location: '南京', owner: '李十三', applyTime: '2024-01-19 16:45:00', specs: { cpu: '16核', memory: '64GB', storage: '1TB', gpu: 'NVIDIA T4 x 2' } },
];

// 待审核任务
export const mockPendingTasks = [
  { id: 'TASK-003', name: '智能推荐系统模型', publisher: '王五', budget: 80000, createdAt: '2024-01-20 11:00:00', description: '基于用户行为数据的智能推荐模型训练' },
  { id: 'TASK-007', name: '图像识别模型', publisher: '王五', budget: 60000, createdAt: '2024-01-19 15:30:00', description: '工业质检场景下的图像识别模型' },
];
