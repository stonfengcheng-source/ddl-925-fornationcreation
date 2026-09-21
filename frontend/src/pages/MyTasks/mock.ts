/**
 * MyTasks 页面 Mock 数据
 * 我的任务管理页面使用的模拟数据
 */

import type { TrainingTask, TrainingStatus } from '../../types/training';

// 我发布的任务
export const mockPublishedTasks: (TrainingTask & {
  applicants: number;
  approvedNodes: number;
  myRole: 'publisher' | 'participant';
})[] = [
  {
    id: 'TASK-001',
    name: '医疗影像分类模型训练',
    description: '基于联邦学习的肺部CT影像分类模型',
    status: 'running',
    createdAt: '2024-01-15T08:00:00Z',
    updatedAt: '2024-01-20T14:30:00Z',
    startedAt: '2024-01-15T09:00:00Z',
    ownerId: 'USER-001',
    ownerName: '张三',
    modelType: 'ResNet50',
    datasetId: 'DATA-001',
    datasetName: '肺部CT数据集',
    totalRounds: 100,
    currentRound: 67,
    targetAccuracy: 0.95,
    currentAccuracy: 0.923,
    participantCount: 5,
    rewardPool: 50000,
    rewardCurrency: 'CNY',
    applicants: 8,
    approvedNodes: 5,
    myRole: 'publisher',
  },
  {
    id: 'TASK-002',
    name: '金融风控预测模型',
    description: '多银行联合风控模型训练',
    status: 'completed',
    createdAt: '2024-01-10T10:00:00Z',
    updatedAt: '2024-01-18T16:00:00Z',
    startedAt: '2024-01-10T10:30:00Z',
    completedAt: '2024-01-18T16:00:00Z',
    ownerId: 'USER-001',
    ownerName: '张三',
    modelType: 'XGBoost',
    datasetId: 'DATA-002',
    datasetName: '风控特征数据集',
    totalRounds: 50,
    currentRound: 50,
    targetAccuracy: 0.92,
    currentAccuracy: 0.941,
    participantCount: 8,
    rewardPool: 100000,
    rewardCurrency: 'CNY',
    applicants: 12,
    approvedNodes: 8,
    myRole: 'publisher',
  },
  {
    id: 'TASK-004',
    name: '语音识别增强模型',
    description: '多方言语音识别模型联邦训练',
    status: 'pending',
    createdAt: '2024-01-20T14:00:00Z',
    updatedAt: '2024-01-20T14:00:00Z',
    ownerId: 'USER-001',
    ownerName: '张三',
    modelType: 'Wave2Vec2',
    datasetId: 'DATA-004',
    datasetName: '方言语音数据集',
    totalRounds: 120,
    currentRound: 0,
    targetAccuracy: 0.9,
    participantCount: 0,
    rewardPool: 120000,
    rewardCurrency: 'CNY',
    applicants: 3,
    approvedNodes: 0,
    myRole: 'publisher',
  },
];

// 我参与的任务
export const mockParticipatedTasks: (TrainingTask & {
  myNodeId: string;
  myContribution: number;
  myReward: number;
  myRole: 'publisher' | 'participant';
})[] = [
  {
    id: 'TASK-003',
    name: '智能推荐系统模型',
    description: '跨平台用户行为推荐模型',
    status: 'paused',
    createdAt: '2024-01-12T09:00:00Z',
    updatedAt: '2024-01-19T11:00:00Z',
    startedAt: '2024-01-12T10:00:00Z',
    ownerId: 'USER-003',
    ownerName: '王五',
    modelType: 'DeepFM',
    datasetId: 'DATA-003',
    datasetName: '用户行为数据集',
    totalRounds: 80,
    currentRound: 35,
    targetAccuracy: 0.88,
    currentAccuracy: 0.856,
    participantCount: 6,
    rewardPool: 80000,
    rewardCurrency: 'CNY',
    myNodeId: 'NODE-MY-001',
    myContribution: 87.5,
    myReward: 5200,
    myRole: 'participant',
  },
  {
    id: 'TASK-005',
    name: '异常检测模型',
    description: '工业设备异常检测联邦模型',
    status: 'failed',
    createdAt: '2024-01-08T11:00:00Z',
    updatedAt: '2024-01-14T09:00:00Z',
    startedAt: '2024-01-08T11:30:00Z',
    ownerId: 'USER-004',
    ownerName: '赵六',
    modelType: 'AutoEncoder',
    datasetId: 'DATA-005',
    datasetName: '工业传感器数据集',
    totalRounds: 60,
    currentRound: 28,
    targetAccuracy: 0.85,
    currentAccuracy: 0.72,
    participantCount: 4,
    rewardPool: 30000,
    rewardCurrency: 'CNY',
    myNodeId: 'NODE-MY-002',
    myContribution: 82.3,
    myReward: 1800,
    myRole: 'participant',
  },
];

// 待审核的申请
export const mockPendingApplications = [
  {
    id: 'APP-001',
    taskId: 'TASK-001',
    taskName: '医疗影像分类模型训练',
    nodeId: 'NODE-006',
    nodeName: '成都医院节点',
    applicantName: '李明',
    organization: '成都华西医院',
    dataSize: 8000,
    applyTime: '2024-01-20T10:00:00Z',
    status: 'pending',
  },
  {
    id: 'APP-002',
    taskId: 'TASK-001',
    taskName: '医疗影像分类模型训练',
    nodeId: 'NODE-007',
    nodeName: '武汉医院节点',
    applicantName: '王芳',
    organization: '武汉同济医院',
    dataSize: 6000,
    applyTime: '2024-01-20T08:30:00Z',
    status: 'pending',
  },
  {
    id: 'APP-003',
    taskId: 'TASK-004',
    taskName: '语音识别增强模型',
    nodeId: 'NODE-008',
    nodeName: '四川方言节点',
    applicantName: '张强',
    organization: '四川大学',
    dataSize: 2000,
    applyTime: '2024-01-20T09:15:00Z',
    status: 'pending',
  },
];

// 任务统计数据
export const mockTaskStatistics = {
  published: {
    total: 3,
    running: 1,
    pending: 1,
    completed: 1,
    failed: 0,
    totalRewardPool: 270000,
    totalDistributed: 150000,
  },
  participated: {
    total: 2,
    running: 0,
    paused: 1,
    failed: 1,
    totalEarned: 7000,
    totalContribution: 169.8,
  },
  pendingApplications: 3,
};

// 筛选选项
export const mockFilterOptions = {
  status: [
    { value: 'all', label: '全部状态', color: 'default' },
    { value: 'pending', label: '待开始', color: 'default' },
    { value: 'running', label: '运行中', color: 'processing' },
    { value: 'paused', label: '已暂停', color: 'warning' },
    { value: 'completed', label: '已完成', color: 'success' },
    { value: 'failed', label: '失败', color: 'error' },
  ],
  categories: [
    { value: 'all', label: '全部类别' },
    { value: 'healthcare', label: '医疗健康' },
    { value: 'finance', label: '金融科技' },
    { value: 'retail', label: '智慧零售' },
    { value: 'manufacturing', label: '智能制造' },
    { value: 'other', label: '其他' },
  ],
  sortBy: [
    { value: 'newest', label: '最新创建' },
    { value: 'updated', label: '最近更新' },
    { value: 'reward', label: '奖励金额' },
    { value: 'progress', label: '训练进度' },
  ],
};

// 任务状态颜色映射
export const statusColorMap: Record<TrainingStatus, string> = {
  pending: 'default',
  running: 'processing',
  paused: 'warning',
  completed: 'success',
  failed: 'error',
  cancelled: 'default',
};

// 任务状态文本映射
export const statusTextMap: Record<TrainingStatus, string> = {
  pending: '待开始',
  running: '运行中',
  paused: '已暂停',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};
