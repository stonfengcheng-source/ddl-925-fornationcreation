/**
 * TaskDetail 页面 Mock 数据
 * 任务详情页使用的模拟数据
 */

import type {
  TrainingTask,
  TrainingNode,
  TrainingConfig,
  TrainingLog,
  NodeContribution,
} from '../../types/training';

// 任务详情数据
export const mockTaskDetail: TrainingTask & {
  tags: string[];
  category: string;
  requirements: {
    minDataSize: number;
    minNodes: number;
    maxNodes: number;
    dataFormat: string[];
    privacyLevel: string;
  };
  publisher: {
    id: string;
    name: string;
    avatar: string;
    organization: string;
    verified: boolean;
    rating: number;
    completedTasks: number;
    joinDate: string;
  };
} = {
  id: 'TASK-001',
  name: '医疗影像分类模型训练',
  description:
    '基于联邦学习的肺部CT影像分类模型训练项目。旨在通过多方协作，在不泄露原始数据的前提下，训练出高精度的医疗影像识别模型。适用于早期肺癌筛查辅助诊断场景。',
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
  tags: ['医疗', '影像识别', '联邦学习', '深度学习'],
  category: '医疗健康',
  requirements: {
    minDataSize: 5000,
    minNodes: 3,
    maxNodes: 10,
    dataFormat: ['DICOM', 'NIfTI', 'PNG'],
    privacyLevel: '高',
  },
  publisher: {
    id: 'USER-001',
    name: '张三',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=zhangsan',
    organization: '北京协和医院',
    verified: true,
    rating: 4.9,
    completedTasks: 12,
    joinDate: '2023-06-15',
  },
};

// 参与方列表
export const mockParticipants: TrainingNode[] = [
  {
    id: 'NODE-001',
    name: '北京医院节点',
    nodeId: 'HOSPITAL_BJ_001',
    status: 'training',
    role: 'trainer',
    taskId: 'TASK-001',
    joinedAt: '2024-01-15T09:00:00Z',
    lastHeartbeat: '2024-01-20T14:29:55Z',
    dataSampleCount: 15000,
    contributionScore: 92.5,
    earnedReward: 8250,
    latency: 45,
    computePower: 12.5,
    currentRound: 67,
    trainingProgress: 85,
  },
  {
    id: 'NODE-002',
    name: '上海医院节点',
    nodeId: 'HOSPITAL_SH_001',
    status: 'training',
    role: 'trainer',
    taskId: 'TASK-001',
    joinedAt: '2024-01-15T09:05:00Z',
    lastHeartbeat: '2024-01-20T14:29:58Z',
    dataSampleCount: 12000,
    contributionScore: 88.3,
    earnedReward: 7350,
    latency: 52,
    computePower: 10.8,
    currentRound: 67,
    trainingProgress: 82,
  },
  {
    id: 'NODE-003',
    name: '广州医院节点',
    nodeId: 'HOSPITAL_GZ_001',
    status: 'online',
    role: 'trainer',
    taskId: 'TASK-001',
    joinedAt: '2024-01-15T09:10:00Z',
    lastHeartbeat: '2024-01-20T14:29:50Z',
    dataSampleCount: 10000,
    contributionScore: 85.7,
    earnedReward: 6900,
    latency: 68,
    computePower: 9.2,
    currentRound: 66,
    trainingProgress: 100,
  },
  {
    id: 'NODE-004',
    name: '中心聚合节点',
    nodeId: 'AGGREGATOR_001',
    status: 'syncing',
    role: 'aggregator',
    taskId: 'TASK-001',
    joinedAt: '2024-01-15T09:00:00Z',
    lastHeartbeat: '2024-01-20T14:30:00Z',
    dataSampleCount: 0,
    contributionScore: 95.0,
    earnedReward: 5000,
    latency: 25,
    computePower: 25.0,
    currentRound: 67,
    trainingProgress: 90,
  },
  {
    id: 'NODE-005',
    name: '深圳医院节点',
    nodeId: 'HOSPITAL_SZ_001',
    status: 'error',
    role: 'trainer',
    taskId: 'TASK-001',
    joinedAt: '2024-01-15T09:15:00Z',
    lastHeartbeat: '2024-01-20T14:20:00Z',
    dataSampleCount: 8000,
    contributionScore: 72.4,
    earnedReward: 2500,
    latency: 150,
    computePower: 7.5,
    currentRound: 65,
    trainingProgress: 0,
  },
];

// 训练配置详情
export const mockTaskConfig: TrainingConfig = {
  taskId: 'TASK-001',
  modelType: 'ResNet50',
  optimizer: 'Adam',
  learningRate: 0.001,
  batchSize: 32,
  epochs: 5,
  aggregationStrategy: 'fedavg',
  minNodes: 3,
  maxNodes: 10,
  timeoutPerRound: 300,
  targetAccuracy: 0.95,
  maxRounds: 100,
  differentialPrivacy: {
    enabled: true,
    epsilon: 1.0,
    delta: 0.0001,
  },
};

// 状态时间线
export const mockTaskTimeline = [
  {
    id: '1',
    status: 'created',
    title: '任务创建',
    description: '任务已创建并发布到平台',
    timestamp: '2024-01-15T08:00:00Z',
    operator: '张三',
  },
  {
    id: '2',
    status: 'published',
    title: '任务发布',
    description: '任务已公开发布，等待节点加入',
    timestamp: '2024-01-15T08:30:00Z',
    operator: '系统',
  },
  {
    id: '3',
    status: 'matched',
    title: '节点匹配完成',
    description: '已成功匹配 5 个参与节点',
    timestamp: '2024-01-15T09:00:00Z',
    operator: '系统',
  },
  {
    id: '4',
    status: 'started',
    title: '训练开始',
    description: '联邦学习训练正式开始',
    timestamp: '2024-01-15T09:00:00Z',
    operator: '系统',
  },
  {
    id: '5',
    status: 'milestone',
    title: '达到 50 轮',
    description: '训练进度达到 50%，准确率 89.5%',
    timestamp: '2024-01-18T10:30:00Z',
    operator: '系统',
  },
  {
    id: '6',
    status: 'progress',
    title: '当前进度',
    description: '已完成 67 轮训练，准确率 92.3%',
    timestamp: '2024-01-20T14:30:00Z',
    operator: '系统',
  },
];

// 任务日志
export const mockTaskLogs: TrainingLog[] = [
  {
    id: 'LOG-001',
    taskId: 'TASK-001',
    nodeId: 'NODE-001',
    level: 'info',
    message: '完成第 67 轮本地训练，loss: 0.1823',
    round: 67,
    timestamp: '2024-01-20T14:28:00Z',
    metadata: { localEpochs: 5, samplesProcessed: 15000 },
  },
  {
    id: 'LOG-002',
    taskId: 'TASK-001',
    nodeId: 'NODE-002',
    level: 'info',
    message: '完成第 67 轮本地训练，loss: 0.1856',
    round: 67,
    timestamp: '2024-01-20T14:28:15Z',
    metadata: { localEpochs: 5, samplesProcessed: 12000 },
  },
  {
    id: 'LOG-003',
    taskId: 'TASK-001',
    nodeId: 'NODE-004',
    level: 'info',
    message: '收到 4 个节点的模型更新，开始聚合',
    round: 67,
    timestamp: '2024-01-20T14:29:00Z',
  },
  {
    id: 'LOG-004',
    taskId: 'TASK-001',
    nodeId: 'NODE-004',
    level: 'info',
    message: '第 67 轮聚合完成，全局 loss: 0.1856, accuracy: 0.9234',
    round: 67,
    timestamp: '2024-01-20T14:30:00Z',
  },
  {
    id: 'LOG-005',
    taskId: 'TASK-001',
    nodeId: 'NODE-005',
    level: 'error',
    message: '节点连接超时，无法参与第 67 轮训练',
    round: 67,
    timestamp: '2024-01-20T14:20:00Z',
    metadata: { errorCode: 'TIMEOUT', retryCount: 3 },
  },
];

// 节点贡献度
export const mockNodeContributions: NodeContribution[] = [
  {
    nodeId: 'NODE-001',
    nodeName: '北京医院节点',
    taskId: 'TASK-001',
    dataQualityScore: 95,
    dataQuantityScore: 90,
    computationScore: 92,
    timelinessScore: 95,
    overallScore: 92.5,
    sampleCount: 15000,
    roundsParticipated: 67,
    rewardAmount: 8250,
    lastUpdated: '2024-01-20T14:30:00Z',
  },
  {
    nodeId: 'NODE-002',
    nodeName: '上海医院节点',
    taskId: 'TASK-001',
    dataQualityScore: 92,
    dataQuantityScore: 85,
    computationScore: 88,
    timelinessScore: 88,
    overallScore: 88.3,
    sampleCount: 12000,
    roundsParticipated: 67,
    rewardAmount: 7350,
    lastUpdated: '2024-01-20T14:30:00Z',
  },
  {
    nodeId: 'NODE-003',
    nodeName: '广州医院节点',
    taskId: 'TASK-001',
    dataQualityScore: 90,
    dataQuantityScore: 80,
    computationScore: 85,
    timelinessScore: 88,
    overallScore: 85.7,
    sampleCount: 10000,
    roundsParticipated: 66,
    rewardAmount: 6900,
    lastUpdated: '2024-01-20T14:30:00Z',
  },
  {
    nodeId: 'NODE-004',
    nodeName: '中心聚合节点',
    taskId: 'TASK-001',
    dataQualityScore: 98,
    dataQuantityScore: 0,
    computationScore: 98,
    timelinessScore: 95,
    overallScore: 95.0,
    sampleCount: 0,
    roundsParticipated: 67,
    rewardAmount: 5000,
    lastUpdated: '2024-01-20T14:30:00Z',
  },
  {
    nodeId: 'NODE-005',
    nodeName: '深圳医院节点',
    taskId: 'TASK-001',
    dataQualityScore: 85,
    dataQuantityScore: 70,
    computationScore: 75,
    timelinessScore: 60,
    overallScore: 72.4,
    sampleCount: 8000,
    roundsParticipated: 65,
    rewardAmount: 2500,
    lastUpdated: '2024-01-20T14:20:00Z',
  },
];

// 相关任务推荐
export const mockRelatedTasks = [
  {
    id: 'TASK-002',
    name: '金融风控预测模型',
    category: '金融科技',
    rewardPool: 100000,
    status: 'completed',
    participantCount: 8,
  },
  {
    id: 'TASK-006',
    name: '眼底病变检测模型',
    category: '医疗健康',
    rewardPool: 60000,
    status: 'running',
    participantCount: 4,
  },
  {
    id: 'TASK-007',
    name: '药物分子筛选模型',
    category: '医疗健康',
    rewardPool: 80000,
    status: 'pending',
    participantCount: 0,
  },
];
